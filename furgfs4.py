import os
import struct
import sys
import time
from datetime import datetime

# Configurações do Sistema de Arquivos
MAGIC = b"FURG"
BLOCK_SIZE = 2048
MAX_FILENAME = 32
MAX_FILES = 128

FREE_BLOCK = -1
EOF_BLOCK = -2

# Header (24 bytes): Magic(4s), BlockSize(I), TotalSize(I), FatOffset(I), DirOffset(I), DataOffset(I)
HEADER_FORMAT = "<4sIIIII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Entry (50 bytes): Active(B), Protected(B), Name(32s), Size(I), FirstBlock(i), CreatedAt(I), ModifiedAt(I)
ENTRY_FORMAT = "<BB32sIiII"
ENTRY_SIZE = struct.calcsize(ENTRY_FORMAT)


class FURGfs4:
    def __init__(self, fs_path):
        self.fs_path = fs_path

    def _read_header(self, f):
        f.seek(0)
        data = f.read(HEADER_SIZE)
        magic, block_size, total_size, fat_offset, dir_offset, data_offset = struct.unpack(HEADER_FORMAT, data)

        if magic != MAGIC:
            raise ValueError("Arquivo informado não é um sistema FURGfs4 válido.")

        return {
            "block_size": block_size,
            "total_size": total_size,
            "fat_offset": fat_offset,
            "dir_offset": dir_offset,
            "data_offset": data_offset,
            "num_blocks": (total_size - data_offset) // block_size,
        }

    # --- Cria o sistema de arquivos
    def create_fs(self, size_mb):
        total_size = size_mb * 1024 * 1024
        dir_size = MAX_FILES * ENTRY_SIZE
        fat_offset = HEADER_SIZE

        num_blocks = (total_size - (HEADER_SIZE + dir_size)) // (BLOCK_SIZE + 4)
        dir_offset = fat_offset + (num_blocks * 4)
        data_offset = dir_offset + dir_size

        with open(self.fs_path, "wb") as f:
            # 1. Escreve o Cabeçalho
            f.write(struct.pack(HEADER_FORMAT, MAGIC, BLOCK_SIZE, total_size, fat_offset, dir_offset, data_offset))

            # 2. Inicializa Tabela FAT
            f.seek(fat_offset)
            f.write(struct.pack(f"<{num_blocks}i", *[FREE_BLOCK] * num_blocks))

            # 3. Inicializa Diretório Raiz
            f.seek(dir_offset)
            empty_entry = struct.pack(ENTRY_FORMAT, 0, 0, b"", 0, -1, 0, 0)
            for _ in range(MAX_FILES):
                f.write(empty_entry)

            # 4. Ajusta tamanho do arquivo
            f.truncate(total_size)

        print(f"Sistema FURGfs4 criado com sucesso ({size_mb} MB) em '{self.fs_path}'.")

    # --- AUXILIARES FAT E DIRETÓRIO ---

    # Lê a FAT binária do disco e a converte em uma lista manipulável do Python.
    def _read_fat(self, f, h):
        f.seek(h["fat_offset"])
        return list(struct.unpack(f"<{h['num_blocks']}i", f.read(h["num_blocks"] * 4)))

    # Pega a lista de inteiros da FAT modificada em memória e a grava de volta no arquivo do disco virtual.
    def _write_fat(self, f, h, fat):
        f.seek(h["fat_offset"])
        f.write(struct.pack(f"<{h['num_blocks']}i", *fat))

    # Lê a tabela do Diretório Raiz no disco virtual,
    # filtra apenas os arquivos válidos (ativos) e
    # converte-os em uma lista de dicionários Python fáceis de manipular.
    def _read_dir(self, f, h):
        f.seek(h["dir_offset"])
        entries = []

        for i in range(MAX_FILES):
            raw = f.read(ENTRY_SIZE)
            active, prot, name_raw, size, first_block, created_at, modified_at = struct.unpack(ENTRY_FORMAT, raw)
            if active:
                name = name_raw.decode("utf-8", errors="ignore").rstrip("\x00")
                entries.append({
                    "index": i,
                    "active": active,
                    "protected": prot,
                    "name": name,
                    "size": size,
                    "first_block": first_block,
                    "created_at": created_at,
                    "modified_at": modified_at,
                })
        return entries

    # --- OPERAÇÕES DO SISTEMA DE ARQUIVOS ---

    # --- Importar um arquivo do SO real para dentro do disco virtual.
    def cp_in(self, external_file, internal_name):
        if not os.path.exists(external_file):
            print("Erro: Arquivo externo não encontrado.")
            return

        file_size = os.path.getsize(external_file)
        blocks_needed = (file_size + BLOCK_SIZE - 1) // BLOCK_SIZE if file_size > 0 else 1

        with open(self.fs_path, "r+b") as f:
            h = self._read_header(f)
            fat = self._read_fat(f, h)
            entries = self._read_dir(f, h)

            if any(e["name"] == internal_name for e in entries):
                print(f"Erro: O arquivo '{internal_name}' já existe no FURGfs4.")
                return

            free_indices = [idx for idx, val in enumerate(fat) if val == FREE_BLOCK]
            if len(free_indices) < blocks_needed:
                print("Erro: Espaço insuficiente no FURGfs4.")
                return

            # Busca slot livre no diretório
            f.seek(h["dir_offset"])
            empty_slot = -1
            for idx in range(MAX_FILES):
                raw = f.read(ENTRY_SIZE)
                active = struct.unpack(ENTRY_FORMAT, raw)[0]
                if not active:
                    empty_slot = idx
                    break

            if empty_slot == -1:
                print("Erro: Diretório raiz cheio.")
                return

            # Aloca blocos na FAT
            allocated_blocks = free_indices[:blocks_needed]
            for i in range(len(allocated_blocks) - 1):
                fat[allocated_blocks[i]] = allocated_blocks[i + 1]
            fat[allocated_blocks[-1]] = EOF_BLOCK
            self._write_fat(f, h, fat)

            # Escreve dados nos blocos
            with open(external_file, "rb") as ext_f:
                for blk in allocated_blocks:
                    buffer = ext_f.read(BLOCK_SIZE)
                    f.seek(h["data_offset"] + (blk * BLOCK_SIZE))
                    f.write(buffer)

            # Grava entrada do diretório
            f.seek(h["dir_offset"] + (empty_slot * ENTRY_SIZE))
            name_bytes = internal_name.encode("utf-8")[:MAX_FILENAME].ljust(MAX_FILENAME, b"\x00")
            now = int(time.time())
            f.write(struct.pack(ENTRY_FORMAT, 1, 0, name_bytes, file_size, allocated_blocks[0], now, now))

        print(f"Arquivo '{external_file}' copiado para FURGfs4 como '{internal_name}'.")

    # --- Exportar um arquivo do disco virtual para o SO real.
    def cp_out(self, internal_name, external_file):
        with open(self.fs_path, "rb") as f:
            h = self._read_header(f)
            fat = self._read_fat(f, h)
            entries = self._read_dir(f, h)

            entry = next((e for e in entries if e["name"] == internal_name), None)
            if not entry:
                print(f"Erro: Arquivo '{internal_name}' não encontrado.")
                return

            curr_block = entry["first_block"]
            remaining_bytes = entry["size"]

            with open(external_file, "wb") as ext_f:
                while curr_block != EOF_BLOCK and remaining_bytes > 0:
                    f.seek(h["data_offset"] + (curr_block * BLOCK_SIZE))
                    read_size = min(BLOCK_SIZE, remaining_bytes)
                    ext_f.write(f.read(read_size))
                    remaining_bytes -= read_size
                    curr_block = fat[curr_block]

        print(f"Arquivo '{internal_name}' extraído para '{external_file}'.")

    # --- Reanomear arquivo
    def mv(self, old_name, new_name):
        with open(self.fs_path, "r+b") as f:
            h = self._read_header(f)
            entries = self._read_dir(f, h)

            entry = next((e for e in entries if e["name"] == old_name), None)
            if not entry:
                print(f"Erro: Arquivo '{old_name}' não encontrado.")
                return

            f.seek(h["dir_offset"] + (entry["index"] * ENTRY_SIZE))
            active, prot, _, size, first_blk, created_at, _ = struct.unpack(ENTRY_FORMAT, f.read(ENTRY_SIZE))

            f.seek(h["dir_offset"] + (entry["index"] * ENTRY_SIZE))
            new_name_bytes = new_name.encode("utf-8")[:MAX_FILENAME].ljust(MAX_FILENAME, b"\x00")
            now = int(time.time())
            f.write(struct.pack(ENTRY_FORMAT, active, prot, new_name_bytes, size, first_blk, created_at, now))

        print(f"Arquivo '{old_name}' renomeado para '{new_name}'.")

    # --- Remover arquivo.
    def rm(self, name):
        with open(self.fs_path, "r+b") as f:
            h = self._read_header(f)
            fat = self._read_fat(f, h)
            entries = self._read_dir(f, h)

            entry = next((e for e in entries if e["name"] == name), None)
            if not entry:
                print(f"Erro: Arquivo '{name}' não encontrado.")
                return

            if entry["protected"] == 1:
                print(f"Erro: Arquivo '{name}' está protegido contra exclusão.")
                return

            # Libera cadeia de blocos
            curr_block = entry["first_block"]
            while curr_block != EOF_BLOCK and curr_block != FREE_BLOCK:
                next_block = fat[curr_block]
                fat[curr_block] = FREE_BLOCK
                curr_block = next_block

            self._write_fat(f, h, fat)

            # Inativa entrada no diretório
            f.seek(h["dir_offset"] + (entry["index"] * ENTRY_SIZE))
            f.write(struct.pack(ENTRY_FORMAT, 0, 0, b"", 0, -1, 0, 0))

        print(f"Arquivo '{name}' removido com sucesso.")

    # --- Listar arquivos.
    def ls(self):
        with open(self.fs_path, "rb") as f:
            h = self._read_header(f)
            entries = self._read_dir(f, h)
            fat = self._read_fat(f, h)

            print(f"{'NOME':<32} | {'TAM. REAL':<12} | {'ESPAÇO OCUPADO':<15} | {'PROT.'} | {'CRIADO EM':<16} | {'MODIFICADO EM':<16}")
            print("-" * 112)
            for e in entries:
                blk_count = 0
                curr = e["first_block"]
                while curr != EOF_BLOCK and curr != FREE_BLOCK:
                    blk_count += 1
                    curr = fat[curr]

                occupied_size = blk_count * BLOCK_SIZE
                prot_str = "Sim" if e["protected"] else "Não"
                dt_created = datetime.fromtimestamp(e["created_at"]).strftime("%d/%m/%Y %H:%M") if e["created_at"] else "-"
                dt_modified = datetime.fromtimestamp(e["modified_at"]).strftime("%d/%m/%Y %H:%M") if e["modified_at"] else "-"

                print(f"{e['name']:<32} | {e['size']:<12} | {occupied_size:<15} | {prot_str:<5} | {dt_created:<16} | {dt_modified:<16}")

    # --- Exibir espaço livre
    def df(self):
        with open(self.fs_path, "rb") as f:
            h = self._read_header(f)
            fat = self._read_fat(f, h)

            free_blocks = fat.count(FREE_BLOCK)
            free_mb = (free_blocks * BLOCK_SIZE) / (1024 * 1024)
            total_mb = h["total_size"] / (1024 * 1024)

            print(f"Espaço Livre: {free_mb:.2f} MB de {total_mb:.2f} MB ({free_blocks} blocos livres de {h['num_blocks']})")

    # --- Proteger arquivo de exclusão.
    def protect(self, name, status):
        val = 1 if status.lower() == "on" else 0
        with open(self.fs_path, "r+b") as f:
            h = self._read_header(f)
            entries = self._read_dir(f, h)

            entry = next((e for e in entries if e["name"] == name), None)
            if not entry:
                print(f"Erro: Arquivo '{name}' não encontrado.")
                return

            f.seek(h["dir_offset"] + (entry["index"] * ENTRY_SIZE))
            active, _, name_bytes, size, first_blk, created_at, modified_at = struct.unpack(ENTRY_FORMAT, f.read(ENTRY_SIZE))

            f.seek(h["dir_offset"] + (entry["index"] * ENTRY_SIZE))
            f.write(struct.pack(ENTRY_FORMAT, active, val, name_bytes, size, first_blk, created_at, modified_at))

        print(f"Proteção de '{name}' alterada para: {status.upper()}")

    # --- Ativar modo debug
    def debug(self, name):
        with open(self.fs_path, "rb") as f:
            h = self._read_header(f)
            fat = self._read_fat(f, h)
            entries = self._read_dir(f, h)

            entry = next((e for e in entries if e["name"] == name), None)
            if not entry:
                print(f"Erro: Arquivo '{name}' não encontrado.")
                return

            blocks = []
            curr = entry["first_block"]
            while curr != EOF_BLOCK and curr != FREE_BLOCK:
                blocks.append(curr)
                curr = fat[curr]

            print(f"Blocos físicos do arquivo '{name}': {blocks}")

# --- CLI de interação com o usuário
def main():
    if len(sys.argv) < 3:
        print("Uso:")
        print("  python furgfs4.py <arquivo.fs> format <tamanho_em_MB>")
        print("  python furgfs4.py <arquivo.fs> cp_in <origem_ext> <nome_int>")
        print("  python furgfs4.py <arquivo.fs> cp_out <nome_int> <destino_ext>")
        print("  python furgfs4.py <arquivo.fs> ls")
        print("  python furgfs4.py <arquivo.fs> df")
        print("  python furgfs4.py <arquivo.fs> rm <nome_int>")
        print("  python furgfs4.py <arquivo.fs> mv <antigo> <novo>")
        print("  python furgfs4.py <arquivo.fs> protect <nome_int> <on|off>")
        print("  python furgfs4.py <arquivo.fs> debug <nome_int>")
        return

    fs_path = sys.argv[1]
    cmd = sys.argv[2]
    fs = FURGfs4(fs_path)

    if cmd == "format":
        fs.create_fs(int(sys.argv[3]))
    elif cmd == "cp_in":
        fs.cp_in(sys.argv[3], sys.argv[4])
    elif cmd == "cp_out":
        fs.cp_out(sys.argv[3], sys.argv[4])
    elif cmd == "ls":
        fs.ls()
    elif cmd == "df":
        fs.df()
    elif cmd == "rm":
        fs.rm(sys.argv[3])
    elif cmd == "mv":
        fs.mv(sys.argv[3], sys.argv[4])
    elif cmd == "protect":
        fs.protect(sys.argv[3], sys.argv[4])
    elif cmd == "debug":
        fs.debug(sys.argv[3])


if __name__ == "__main__":
    main()