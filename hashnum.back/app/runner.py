import os, re, csv, tempfile, subprocess, threading, time, shlex
from datetime import datetime
from pathlib import Path
from typing import Callable

HASHCAT_BIN = os.getenv("HASHCAT_BIN", "hashcat")
HASHCAT_CMD_TEMPLATE = os.getenv("HASHCAT_CMD_TEMPLATE", "{HASHCAT_BIN}")
ALLOW_EXECUTION = os.getenv("ALLOW_EXECUTION", "true").lower() == "true"

MASK_DIGITS = "?d" * 9
MASK_79 = "79" + MASK_DIGITS


PROG_RE = re.compile(r"Progress.*?:\s*([\d,]+)/([\d,]+).*?\(([\d.,]+)%\)")


def _read_hashes_any(p: Path) -> list[str]:
    if not p.exists():
        return []
    data = p.read_text(encoding="utf-8", errors="ignore")
    if not data.strip():
        return []
    lines = data.splitlines()

    delim = ","
    sample = "\n".join(lines[:2])
    if ";" in sample and sample.count(";") >= sample.count(","):
        delim = ";"
    elif "\t" in sample:
        delim = "\t"

    try:
        rdr = csv.DictReader(lines, delimiter=delim)
        if rdr.fieldnames and any(f.strip().lower() == "hash" for f in rdr.fieldnames):
            key = next(f for f in rdr.fieldnames if f.strip().lower() == "hash")
            out = []
            for row in rdr:
                h = (row.get(key) or "").strip()
                if h:
                    out.append(h)
            if out:
                return out
    except Exception:
        pass

    out = []
    try:
        rdr = csv.reader(lines, delimiter=delim)
        for row in rdr:
            if not row:
                continue
            h = (row[0] or "").strip()
            if h:
                out.append(h)
    except Exception:
        return []
    return out


class RunCallbacks:
    def __init__(
        self, on_log: Callable[[str], None], on_progress: Callable[[float, int, int], None]
    ):
        self.on_log = on_log
        self.on_progress = on_progress


def _build_cmd(args: list[str]) -> list[str]:
    head = HASHCAT_CMD_TEMPLATE.format(HASHCAT_BIN=HASHCAT_BIN)
    return shlex.split(head) + args


def run_hashcat_task(input_file: Path, salt: str, output_csv: Path, cb: RunCallbacks) -> None:
    if not ALLOW_EXECUTION:
        cb.on_log("⛔ Запуск отключён (ALLOW_EXECUTION=false)")
        raise RuntimeError("execution disabled")

    hashes = _read_hashes_any(input_file)
    if not hashes:
        cb.on_log("⚠️ Не удалось прочитать хэши (CSV/TXT).")
        raise RuntimeError("no hashes")

    cb.on_log(f"✔ Найдено хэшей: {len(hashes)}")
    cb.on_log(f"✔ Соль: {salt}")
    cb.on_log("▶ Готовлю список hash:salt…")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_csv.write_text("")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        hashfile = td / "hashes.txt"
        with hashfile.open("w", encoding="utf-8") as f:
            for h in hashes:
                f.write(f"{h}:{salt}\n")

        potfile = td / "gui_md5_digits.potfile"

        common_out = [
            "--outfile",
            str(output_csv),
            "--outfile-format",
            "2",
            "--outfile-autohex-disable",
            "--status",
            "--status-timer",
            "5",
            "--potfile-path",
            str(potfile),
            "--force",
        ]

        cpu_args = [
            "-m",
            "10",
            "-a",
            "3",
            str(hashfile),
            MASK_79,
            "-O",
            "-w",
            "3",
            "-D",
            "1",
        ] + common_out

        def _run_once(args: list[str]) -> None:
            cmd = _build_cmd(args)
            cb.on_log("▶ Запуск: " + " ".join(cmd))
            start = datetime.now()
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )

            saw_100 = False
            last_out = datetime.now()

            def reader():
                nonlocal saw_100, last_out
                for line in proc.stdout or []:
                    s = line.rstrip()
                    if not s:
                        continue
                    last_out = datetime.now()
                    cb.on_log(s)
                    m = PROG_RE.search(s)
                    if m:
                        percent = float(m.group(3).replace(",", "."))
                        cb.on_progress(percent, 0, len(hashes))
                        if percent >= 100.0:
                            saw_100 = True
                            try:
                                proc.terminate()
                            except Exception:
                                pass

            t = threading.Thread(target=reader, daemon=True)
            t.start()
            while True:
                try:
                    proc.wait(timeout=0.5)
                    break
                except subprocess.TimeoutExpired:
                    if saw_100 and (datetime.now() - last_out).total_seconds() > 5:
                        try:
                            proc.kill()
                        except Exception:
                            pass
            t.join(timeout=2)

        _run_once(cpu_args)

        cb.on_log("▶ Сбор статистики (--show)…")
        time.sleep(0.2)
        show_cmd = _build_cmd(["--show", "-m", "10", str(hashfile), "--potfile-path", str(potfile)])
        res = subprocess.run(show_cmd, capture_output=True, text=True)
        cracked_lines = [ln for ln in (res.stdout or "").splitlines() if ln.strip()]
        try:
            with open(output_csv, "r", encoding="utf-8", errors="ignore") as fo:
                plain_lines = [ln for ln in fo.read().splitlines() if ln.strip()]
        except Exception:
            plain_lines = []
        cracked = max(len(cracked_lines), len(plain_lines))
        total = len(hashes)
        left = max(0, total - cracked)
        cb.on_log(f"▶ Расхэшировано: {cracked} из {total}. Осталось: {left}")
        cb.on_progress(100.0, cracked, total)

        if cracked:
            cb.on_log(f"✅ Готово! Результат: {output_csv}")
        else:
            cb.on_log(f"⚠️ Ничего не найдено. Файл записан: {output_csv}")
