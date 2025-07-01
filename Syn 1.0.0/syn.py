from typing import Dict, List, Union

# === 글로벌 라벨 테이블 및 콜 스택 ===
label_table: Dict[str, int] = {}
call_stack: List[int] = []

# === 데이터 구조 정의 ===

version = "1.0.0"

class Bit:
    def __init__(self, name: str, value: int = 0, constant: bool = False):
        self.name = name
        self.value = int(value)
        self.constant = constant

    def set(self, value: int):
        if not self.constant:
            self.value = int(value)

    def rev(self):
        if not self.constant:
            self.value ^= 1  # XOR 토글


class Gate:
    def __init__(self, gate_type: str, inputs: List[Bit]):
        self.gate_type = gate_type
        self.inputs = inputs

    def evaluate(self) -> int:
        vals = [bit.value for bit in self.inputs]
        if self.gate_type == "AND":
            return int(all(vals))
        elif self.gate_type == "OR":
            return int(any(vals))
        elif self.gate_type == "NOT":
            return int(not vals[0])
        elif self.gate_type == "XOR":
            return int(sum(vals) % 2)
        elif self.gate_type == "NAND":
            return int(not all(vals))
        elif self.gate_type == "NOR":
            return int(not any(vals))
        else:
            raise ValueError(f"Unknown gate: {self.gate_type}")


class Connection:
    def __init__(self, output_bit: Bit, gate: Gate):
        self.output_bit = output_bit
        self.gate = gate

    def update(self):
        self.output_bit.set(self.gate.evaluate())


# === 표준 비트 초기화 ===

standard_bits: Dict[str, Bit] = {
    f"{b}x{str(i).zfill(4)}": Bit(f"{b}x{str(i).zfill(4)}", 0, constant=False)
    for b in range(1, 10)
    for i in range(1, 10000)
}
# 고정 비트 (C가 붙은 경우)
standard_bits.update({
    f"{b}x{str(i).zfill(4)}C": Bit(f"{b}x{str(i).zfill(4)}C", 0, constant=True)
    for b in range(1, 10)
    for i in range(1, 10000)
})

# 사용자 정의 비트 저장소
user_bits: Dict[str, Bit] = {}
byte_groups: Dict[str, Dict[int, Bit]] = {}

# 게이트 및 연결 저장소
connections: List[Connection] = []

# === .syn 파일 로딩 함수 ===
from typing import List

def load_syn_file(filename: str) -> List[str]:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f.readlines()]
    return lines


import re

# 유틸: 비트 검색 함수
def find_bit(name: str) -> Bit:
    if name in user_bits:
        return user_bits[name]
    elif name in standard_bits:
        return standard_bits[name]
    # 바이트 내부 비트 접근 (예: byte1[3])
    byte_match = re.match(r"(\w+)\[(\d+)\]", name)
    if byte_match:
        group_name = byte_match.group(1)
        index = int(byte_match.group(2))
        if group_name in byte_groups and index in byte_groups[group_name]:
            return byte_groups[group_name][index]
    # 자동 생성: 사용자 정의 비트가 없으면 새로 만듦
    if name.strip() == "":
        raise ValueError("비트 이름이 비어 있습니다.")
    new_bit = Bit(name, 0)
    user_bits[name] = new_bit
    return new_bit

def execute_line(line: str):
    global current_line
    try:
        # mov 명령
        if line.startswith("mov "):
            m = re.match(r"mov (.+?) *: *(.+?);", line)
            if m:
                src = m.group(1).strip()
                dst = m.group(2).strip()
                src_bit = find_bit(src)
                dst_bit = find_bit(dst)
                dst_bit.set(src_bit.value)
                src_bit.set(0)
            return
        # swc 명령
        if line.startswith("swc "):
            m = re.match(r"swc (.+?) *: *(.+?);", line)
            if m:
                bit1 = find_bit(m.group(1).strip())
                bit2 = find_bit(m.group(2).strip())
                bit1.value, bit2.value = bit2.value, bit1.value
            return
        # slp 명령
        if line.startswith("slp "):
            m = re.match(r"slp ([\d.]+);", line)
            if m:
                import time
                time.sleep(float(m.group(1)))
            return
        # call 명령
        if line.startswith("call "):
            m = re.match(r"call (\w+);", line)
            if m:
                label = m.group(1)
                if label in label_table:
                    call_stack.append(current_line)
                    current_line = label_table[label]
            return

        # ret 명령
        if line.strip() == "ret;":
            if call_stack:
                current_line = call_stack.pop() + 1
            else:
                current_line += 1  # 스택이 비어도 다음 줄로 진행
            return
        # cln 조건문
        if line.startswith("cln ") and line.endswith(":"):
            condition = line[4:-1].strip()
            if resolve_condition(condition):
                block_start = current_line + 1
                while block_start < len(syn_lines) and syn_lines[block_start].startswith(";"):
                    execute_line(syn_lines[block_start][1:].strip())
                    block_start += 1
            return

        # 문자열 출력
        if line.startswith("out $") and line.endswith("$;"):
            text = line[len("out $"):-2]
            print(text)
            return

        # 비트 출력
        if line.startswith("out &") and line.endswith(";"):
            bitname = line[5:-1].strip()
            if bitname.startswith("(") and bitname.endswith(")"):
                bitname = bitname[1:-1].strip()
            print(find_bit(bitname).value)
            return

        # set 명령
        if line.startswith("set "):
            m = re.match(r"set (.+?) *: *([01]);", line)
            if m:
                bitname, val = m.group(1), int(m.group(2))
                find_bit(bitname).set(val)
            return

        # pop 명령
        if line.startswith("pop "):
            m = re.match(r"pop (.+?);", line)
            if m:
                bitname = m.group(1)
                find_bit(bitname).set(0)
            return

        # rev 명령
        if line.startswith("rev "):
            m = re.match(r"rev (.+?);", line)
            if m:
                bitname = m.group(1)
                find_bit(bitname).rev()
            return

        # sft 명령 (바이트 시프트)
        if line.startswith("sft "):
            m = re.match(r"sft (\w+)\[(\d+):(\d+)\] *: *(-?\d+);", line)
            if m:
                name, start, end, shift_val = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
                group = {}
                if name in byte_groups:
                    group = byte_groups[name]
                elif re.match(r"\d+x", name):
                    # 표준 비트 바이트 처리
                    for i in range(start, end + 1):
                        key = f"{name}{str(i).zfill(4)}"
                        if key in standard_bits:
                            group[i] = standard_bits[key]
                if not group and name not in byte_groups:
                    raise ValueError(f"정의되지 않은 바이트 그룹 또는 비트 범위: {name}")
                indices = list(range(start, end + 1))
                if shift_val > 0:
                    for i in reversed(indices):
                        new_val = group.get(i - shift_val, Bit("", 0)).value
                        group[i].set(new_val)
                elif shift_val < 0:
                    for i in indices:
                        new_val = group.get(i - shift_val, Bit("", 0)).value
                        group[i].set(new_val)
            return

        # slp 명령 (정수, 밀리초 단위)
        if line.startswith("slp "):
            m = re.match(r"slp (\d+);", line)
            if m:
                import time
                time.sleep(int(m.group(1)) / 1000.0)
            return

        # goto 명령
        if line.startswith("goto "):
            m = re.match(r"goto (\d+);", line)
            if m:
                target = int(m.group(1)) - 1
                current_line = target
            return

        # rel bit 선언
        if line.startswith("rel bit"):
            m = re.match(r"rel bit *: *(\w+) *= *([01]);", line)
            if m:
                name, val = m.group(1), int(m.group(2))
                user_bits[name] = Bit(name, val)
            return

        # rel byt 선언
        if line.startswith("rel byt"):
            m = re.match(r"rel byt *: *(\w+)\[(\d+):(\d+)\]", line)
            if m:
                name, start, end = m.group(1), int(m.group(2)), int(m.group(3))
                byte_groups[name] = {}
                for i in range(start, end + 1):
                    bname = f"{name}[{i}]"
                    byte_groups[name][i] = Bit(bname, 0)
                    user_bits[bname] = byte_groups[name][i]
            return

        # con 연결
        if line.startswith("con "):
            m = re.match(r"con (.+?) *~ *gate:(\w+)\((.+?)\);", line)
            if m:
                out_bit = find_bit(m.group(1))
                gate_type = m.group(2)
                input_names = [x.strip() for x in m.group(3).split(",")]
                inputs = [find_bit(name) for name in input_names]
                gate = Gate(gate_type, inputs)
                result = gate.evaluate()
                out_bit.set(result)
                # connections.append(Connection(out_bit, gate))
            return
    except Exception as e:
        print(f"[Syn] ({type(e).__name__}) : {str(e)} [{current_line + 1}번줄]")
        

def resolve_condition(condition: str) -> bool:
    # &표시된 비트를 전부 찾아 실제 값으로 치환
    matches = re.findall(r"&([\w\[\]x]+)", condition)
    for name in matches:
        try:
            bit = find_bit(name)
            condition = condition.replace(f"&{name}", str(bit.value))
        except Exception:
            return False  # 비트가 없으면 조건문은 False로 간주
    try:
        return eval(condition)
    except Exception:
        return False

if __name__ == "__main__":
    import sys
    filename = sys.argv[1] if len(sys.argv) > 1 else "script.syn"
    try:
        syn_lines = load_syn_file(filename)
        print(f"[syn {version}] file : {filename} loading completed...")
        current_line = 0
        # bdl 라벨 미리 스캔
        for idx, line in enumerate(syn_lines):
            if line.startswith("bdl ") and (line.endswith(";") or line.endswith(":")):
                label_name = line[4:-1].strip()
                label_table[label_name] = idx
        while current_line < len(syn_lines):
            line = syn_lines[current_line]
            code_only = line.split("\\", 1)[0].rstrip()
            prev_line = current_line
            execute_line(code_only)
            if current_line == prev_line:
                current_line += 1
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {filename}")