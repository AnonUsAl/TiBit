import hashlib
import colorsys
import json
import copy
import time
import random
import threading
from collections import OrderedDict
import ctypes
import os
import sys
from tkinter import *
from tkinter import messagebox, scrolledtext, ttk, simpledialog
import tkinter as tk
import tkinter.font as tkfont


MINING_DIFFICULTY = 1
MINING_REWARD = 5
GENESIS_PREV_HASH = "0" * 64
BLOCKCHAIN_FILENAME = "improved_tcoin_chain.json"
password_error_times = 0

def set_windows_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def get_app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


SCRIPT_DIR = get_app_base_dir()
BLOCKCHAIN_FILE_PATH = os.path.join(SCRIPT_DIR, BLOCKCHAIN_FILENAME)
LOCK_FILE_PATH = os.path.join(SCRIPT_DIR, "lockon.txt")
Password_hash_file = os.path.join(SCRIPT_DIR, "password_hash.txt")

def restart_program(temp_root):
    try:
        messagebox.showinfo("成功", "密码已经设定，程序将立即重启。", parent=temp_root)
        temp_root.destroy()
        temp_root.update()
        python = sys.executable
        os.execl(python, python, *sys.argv)
    except Exception as e:
        messagebox.showerror("重启失败", f"错误：{str(e)}\n请手动重启")

def lockon(status):
    val = "1" if status in [True, 1, "1"] else "0"
    with open(LOCK_FILE_PATH, "w", encoding='utf-8') as file:
        file.write(val)

def check_lockon():
    try:
        if not os.path.exists(LOCK_FILE_PATH):
            return False
        with open(LOCK_FILE_PATH, "r", encoding='utf-8') as file:
            return file.read(1) == "1"
    except Exception:
        return False

def password_creat():
    temp_root = tk.Tk()
    temp_root.withdraw()
    try:
        while True:
            word = simpledialog.askstring("创建密码", "请输入新密码 (建议8位以上):", show='*', parent=temp_root)
            if word and len(word) >= 8:
                sha256_value = hashlib.sha256(word.encode()).hexdigest()
                with open(Password_hash_file, "w", encoding='utf-8') as file:
                    file.write(sha256_value)

                messagebox.showinfo("成功", "密码已经设定，程序将立即重启。", parent=temp_root)
                temp_root.destroy()
                python = sys.executable
                os.execl(python, python, *sys.argv)

            elif word:
                messagebox.showwarning("提示", "密码至少需要 8 位。", parent=temp_root)
            else:
                if messagebox.askyesno("退出警告", "未设置密码，确定要退出程序吗？", parent=temp_root):
                    temp_root.destroy()
                    sys.exit(0)
    except Exception as e:
        messagebox.showerror("错误", f"保存密码失败: {e}")
        sys.exit(1)

def load_password():
    if os.path.exists(Password_hash_file):
        with open(Password_hash_file, 'r', encoding='utf-8') as f:
            p = f.read().strip()
            if p: return p
    return password_creat()
PASSWORD = load_password()

def password_recover():
    temp_root = tk.Tk()
    temp_root.withdraw()
    try:
        if messagebox.askyesno("安全验证", "是否重置密码并解除锁定？", parent=temp_root):
            while True:
                word = simpledialog.askstring("重置密码", "请输入新密码 (至少8位):", show='*', parent=temp_root)
                if word and len(word) >= 8:
                    sha256_value = hashlib.sha256(word.encode()).hexdigest()
                    with open(Password_hash_file, "w", encoding='utf-8') as file:
                        file.write(sha256_value)

                    lockon(False)
                    messagebox.showinfo("成功", "密码已重置，程序将立即重启。", parent=temp_root)
                    restart_program(temp_root)
                else:
                    if not messagebox.askyesno("提示", "密码过短或已取消。是否重新设定？", parent=temp_root):
                        sys.exit()
        else:
            sys.exit()
    except Exception as e:
        sys.exit()

def check_password(parent=None, max_attempts=3):
    global password_error_times
    dialog_parent = parent if parent else tk.Tk()
    if not parent: dialog_parent.withdraw()

    try:
        if check_lockon():
            messagebox.showwarning("已锁定", "程序处于锁定状态，请先重置密码。", parent=dialog_parent)
            password_recover()
            return False

        while password_error_times < max_attempts:
            ans = simpledialog.askstring("密码验证", f"请输入密码 (剩余 {max_attempts - password_error_times} 次):",
                                         show='*', parent=dialog_parent)
            if ans is None: return False

            ans_hash = hashlib.sha256(ans.encode()).hexdigest()
            if ans_hash == PASSWORD:
                password_error_times = 0
                return True

            password_error_times += 1
            if password_error_times >= max_attempts:
                lockon(True)    
                messagebox.showerror("错误", "错误次数过多，程序已锁定！", parent=dialog_parent)
                password_recover()
                return False
            else:
                messagebox.showerror("错误", "密码错误！", parent=dialog_parent)
    finally:
        if not parent:
            try:
                dialog_parent.destroy()
            except:
                pass
    return False

def start_app():
    set_windows_dpi_awareness()
    root = tk.Tk()
    root.withdraw()

    if not check_password(parent=root):
        sys.exit(1)

    try:
        tcoin = Blockchain()
        BlockchainApp(root, tcoin)
        root.deiconify()   
        root.mainloop()    
    except Exception as e:
        messagebox.showerror("启动错误", f"程序启动失败: {e}")
        sys.exit(1)

class Wallet:
    @staticmethod
    def generate_key_pair():
        private_key = hashlib.sha256(str(time.time() + random.random()).encode()).hexdigest()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()[:40]    
        return public_key, private_key

    @staticmethod
    def sign_transaction(private_key, transaction_data):
        
        tx_string = json.dumps(transaction_data, sort_keys=True)
        signature = hashlib.sha256((tx_string + private_key).encode()).hexdigest()
        return signature

class Blockchain:
    def __init__(self):

        self.pending_transactions = []
        self.chain = []
        self.last_error = ""
        default_pub, default_priv = Wallet.generate_key_pair()
        self.wallets = {"AnonUsAl": default_priv}
        self.addresses = {"AnonUsAl": default_pub}

        loaded = self.load_chain(BLOCKCHAIN_FILE_PATH)
        self.created_genesis = False
        if not loaded:
            self.mine_block(proof=100, previous_hash=GENESIS_PREV_HASH, transactions=[], miner_address="SYSTEM")
            self.created_genesis = True

    @property
    def last_block(self):
        return self.chain[-1] if self.chain else None

    @staticmethod
    def hash_block(block):
        block_copy = {k: v for k, v in block.items() if k != 'hash'}
        ordered = OrderedDict(sorted(block_copy.items()))
        block_string = json.dumps(ordered, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def register_new_wallet(self, user_alias):
        public_key, private_key = Wallet.generate_key_pair()
        self.wallets[user_alias] = private_key
        self.addresses[user_alias] = public_key
        return public_key

    def set_last_error(self, message=""):
        self.last_error = message

    def new_transaction(self, sender, recipient, amount, sender_private_key=None):
       
        try:
            amount = float(amount)
        except ValueError:
            self.set_last_error("交易失败：金额必须是数字。")
            return False

        if amount <= 0:
            self.set_last_error(f"交易失败：金额 {amount} 必须是正数。")
            return False

        
        if sender != "SYSTEM":
            if self.get_balance(sender) < amount:
                self.set_last_error(f"交易失败：{sender} 余额不足。")
                return False

            if sender_private_key is None:
                self.set_last_error("交易失败：用户交易需要私钥进行签名。")
                return False

        transaction_data = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'timestamp': time.time(),
        }

        signature = Wallet.sign_transaction(sender_private_key or "", transaction_data)
        transaction = {**transaction_data, 'signature': signature}

        self.pending_transactions.append(transaction)
        self.set_last_error("")
        return True

    def mine_block(self, proof, previous_hash, transactions, miner_address):
 
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': transactions,
            'proof': proof,
            'previous_hash': previous_hash,
            'miner': miner_address,
        }

        block['hash'] = self.hash_block(block)
        self.chain.append(block)

        received_sigs = {tx.get('signature') for tx in transactions if isinstance(tx, dict)}
        self.pending_transactions = [t for t in self.pending_transactions if t.get('signature') not in received_sigs]

        return block

    def perform_proof_of_work(self, last_proof, transactions, difficulty, max_seconds=None, max_iterations=None,
                              progress_cb=None, progress_every=1000, cancel_event=None):

        proof = 0
        start_time = time.time()
        while not self.is_valid_proof(last_proof, proof, transactions, difficulty):
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("工作量证明已取消。")
            proof += 1
            if progress_cb and proof % progress_every == 0:
                progress_cb(proof, time.time() - start_time)
            if max_iterations is not None and proof >= max_iterations:
                raise RuntimeError("工作量证明超过最大迭代次数，已中止。")
            if max_seconds is not None and (time.time() - start_time) >= max_seconds:
                raise RuntimeError("工作量证明超时，已中止。")
        return proof

    @staticmethod
    def is_valid_proof(last_proof, proof, transactions, difficulty):

        transactions_string = json.dumps(transactions, sort_keys=True).encode()
        guess = f'{last_proof}{proof}{transactions_string}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == '0' * difficulty

    def difficulty_at_index(self, index):

        base = MINING_DIFFICULTY
        adjust = (index // 10)
        return min(base + adjust, 8)

    def get_difficulty(self):
        
        return self.difficulty_at_index(len(self.chain))

    def get_balance(self, user):
       
        balance = 0
        for block in self.chain:
            for tx in block.get('transactions', []):
                if tx.get('sender') == user:
                    balance -= tx.get('amount', 0)
                if tx.get('recipient') == user:
                    balance += tx.get('amount', 0)
        return balance

    def get_all_balances(self):
       
        balances = {}
        for block in self.chain:
            for tx in block.get('transactions', []):
                balances[tx['sender']] = balances.get(tx['sender'], 0) - tx['amount']
                balances[tx['recipient']] = balances.get(tx['recipient'], 0) + tx['amount']

        if "SYSTEM" in balances:
            del balances["SYSTEM"]

        return balances

    def get_chain_validation_error(self):
        if not self.chain:
            return None

        genesis = self.chain[0]
        if genesis.get('previous_hash') != GENESIS_PREV_HASH:
            return "创世区块的 previous_hash 不正确。"

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            prev_block = self.chain[i - 1]

            expected_prev_hash = self.hash_block(prev_block)
            if current_block.get('previous_hash') != expected_prev_hash:
                return f"链条断裂：区块 {i} 的 previous_hash 与 区块 {i - 1} 的哈希不符。"

            last_proof = prev_block.get('proof', 0)
            transactions_to_verify = current_block.get('transactions', [])
            current_difficulty = self.difficulty_at_index(prev_block.get('index', 0))
            if not self.is_valid_proof(last_proof, current_block.get('proof'), transactions_to_verify,
                                       current_difficulty):
                return f"区块 {i} 的工作量证明无效（Nonce={current_block.get('proof')}，难度={current_difficulty}）。"

            expected_hash = self.hash_block(current_block)
            if current_block.get('hash') != expected_hash:
                return f"区块 {i} 的哈希值不正确。期望 {expected_hash}，但区块中为 {current_block.get('hash')}"

        return None

    def is_chain_valid(self):
        error = self.get_chain_validation_error()
        self.set_last_error("" if error is None else error)
        return error is None

    def is_chain_valid_silent(self):
        return self.get_chain_validation_error() is None

    def save_chain(self, filename):

        try:
            data = {
                'chain': self.chain,
                'pending_transactions': self.pending_transactions,
                'wallets': self.wallets,
                'addresses': self.addresses,
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.set_last_error("")
            return True
        except Exception as e:
            self.set_last_error(f"保存失败: {e}")
            return False

    def load_chain(self, filename):
        try:
            prev_chain = self.chain
            prev_pending = self.pending_transactions
            prev_wallets = self.wallets
            prev_addresses = self.addresses

            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.chain = data.get('chain', [])
                self.pending_transactions = data.get('pending_transactions', [])
                self.wallets = data.get('wallets', {"AnonUsAl": "mock_private_key_001"})
                self.addresses = data.get('addresses', {})

            for alias, private_key in self.wallets.items():
                self.addresses.setdefault(alias, hashlib.sha256(private_key.encode()).hexdigest()[:40])

            if not self.is_chain_valid():
                self.chain = prev_chain
                self.pending_transactions = prev_pending
                self.wallets = prev_wallets
                self.addresses = prev_addresses
                return False

            self.set_last_error("")
            return True
        except FileNotFoundError:
            self.set_last_error(f"未找到区块链文件: {filename}")
            return False
        except Exception as e:
            self.set_last_error(f"加载失败: {e}")
            return False

class BlockchainApp:
    def __init__(self, root, blockchain):
        self.blockchain = blockchain
        self.root = root

        self.root.title("TChain Studio")    
        self.root.geometry("1920x1080")    

        self.is_mining_continous = False
        self.mining_interval_var = tk.IntVar(value=100)
        self.mining_interval_ms = self.mining_interval_var.get()
        self.pow_timeout_single_sec = 8
        self.pow_timeout_cont_sec = 3
        self.pow_timeout_single_var = tk.IntVar(value=self.pow_timeout_single_sec)
        self.pow_timeout_cont_var = tk.IntVar(value=self.pow_timeout_cont_sec)
        self.ui_scale_var = tk.DoubleVar(value=1.0)
        self.widget_font_base_sizes = {}
        self.ui_fonts_ready = False
        self.tamper_backup = None
        self.last_pow_attempts = 0
        self.miner_color_map = {}
        self.active_pow_thread = None
        self.active_pow_cancel_event = None
        self.pow_job_token = 0
        self.pow_progress_every = 200

        self.miner_id = "AnonUsAl"
        if self.miner_id not in self.blockchain.wallets:
            self.blockchain.register_new_wallet(self.miner_id)

        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass
        self.apply_ui_scale(self.detect_ui_scale())
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('TButton', padding=6, font=('Arial', 10, 'bold'))
        self.style.map('TButton', foreground=[('active', 'blue'), ('pressed', 'red')])

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)

        left_container = ttk.Frame(main_frame)
        left_container.pack(side=LEFT, fill=Y, padx=10)

        control_canvas = tk.Canvas(left_container, borderwidth=0, highlightthickness=0, height=900)
        control_scroll = ttk.Scrollbar(left_container, orient="vertical", command=control_canvas.yview)
        control_canvas.configure(yscrollcommand=control_scroll.set)

        control_scroll.pack(side=RIGHT, fill=Y)
        control_canvas.pack(side=LEFT, fill=Y, expand=False)

        control_frame = ttk.Frame(control_canvas, padding="5", relief=GROOVE)
        control_window = control_canvas.create_window((0, 0), window=control_frame, anchor="nw")

        def _on_control_configure(event):
            control_canvas.configure(scrollregion=control_canvas.bbox("all"))

        def _on_canvas_configure(event):
            control_canvas.itemconfigure(control_window, width=event.width)

        control_frame.bind("<Configure>", _on_control_configure)
        control_canvas.bind("<Configure>", _on_canvas_configure)

        wallet_frame = ttk.LabelFrame(control_frame, text=f"当前矿工/发送方 ({self.miner_id})", padding="10")
        wallet_frame.pack(pady=10, fill=X)
        ttk.Label(wallet_frame, text="身份/钱包名:", font=('Arial', 10, 'bold')).pack(side=LEFT, padx=5)
        self.miner_id_var = StringVar(value=self.miner_id)
        self.miner_id_entry = ttk.Entry(wallet_frame, textvariable=self.miner_id_var, width=15, state="disabled")
        self.miner_id_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.set_miner_button = ttk.Button(wallet_frame, text="切换/创建钱包", command=self.set_miner, width=15)
        self.set_miner_button.pack(side=LEFT)

        key_frame = ttk.LabelFrame(control_frame, text="当前密钥", padding="10")
        key_frame.pack(pady=5, fill=X)
        ttk.Label(key_frame, text="公钥 (地址)", font=('Arial', 9, 'bold')).pack(anchor=W)
        self.public_key_label = ttk.Label(key_frame, text="-")
        self.public_key_label.pack(anchor=W, pady=(0, 4))
        ttk.Label(key_frame, text="私钥", font=('Arial', 9, 'bold')).pack(anchor=W)
        self.private_key_label = ttk.Label(key_frame, text="-")
        self.private_key_label.pack(anchor=W)

        tx_frame = ttk.LabelFrame(control_frame, text="创建交易 (需私钥签名)", padding="10")
        tx_frame.pack(pady=10, fill=X)

        ttk.Label(tx_frame, text="接收方:", width=10).grid(row=0, column=0, sticky=W, pady=2)
        self.recipient_entry = ttk.Entry(tx_frame)
        self.recipient_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.recipient_entry.insert(0, "")

        ttk.Label(tx_frame, text="金额:", width=10).grid(row=1, column=0, sticky=W, pady=2)
        self.amount_entry = ttk.Entry(tx_frame)
        self.amount_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.amount_entry.insert(0, "10.0")

        self.tx_button = ttk.Button(tx_frame, text="提交交易 (签名)", command=self.create_transaction)
        self.tx_button.grid(row=2, columnspan=2, pady=10, sticky="ew")

        tx_frame.grid_columnconfigure(1, weight=1)

        action_frame = ttk.LabelFrame(control_frame, text="核心操作", padding="10")
        action_frame.pack(pady=10, fill=X)

        ttk.Label(action_frame, text="挖矿模式:", font=('Arial', 10, 'bold')).pack(pady=(5, 0))

        self.mine_button = ttk.Button(action_frame, text="✈单次挖矿 (PoW)", command=self.mine_block_single)
        self.mine_button.pack(pady=5, fill=X)

        self.start_cont_mine_button = ttk.Button(action_frame, text="🚀 开始持续挖矿",
                                                 command=self.start_continuous_mining)
        self.start_cont_mine_button.pack(pady=5, fill=X)

        self.stop_cont_mine_button = ttk.Button(action_frame, text="🛑 停止持续挖矿",
                                                command=self.stop_continuous_mining, state=DISABLED)
        self.stop_cont_mine_button.pack(pady=5, fill=X)
        self.pow_status_label = ttk.Label(action_frame, text="PoW状态: 空闲")
        self.pow_status_label.pack(pady=(5, 0))
        self.pow_attempts_label = ttk.Label(action_frame, text="尝试次数: 0")
        self.pow_attempts_label.pack()

        ttk.Label(action_frame, text="区块链操作:", font=('Arial', 10, 'bold')).pack(pady=(5, 0))

        self.save_button = ttk.Button(action_frame, text="💾保存区块链 (.json)", command=self.save_data)
        self.save_button.pack(pady=5, fill=X)

        self.load_button = ttk.Button(action_frame, text="💽加载区块链 (.json)", command=self.load_data)
        self.load_button.pack(pady=5, fill=X)

        self.validate_button = ttk.Button(action_frame, text="🔗验证区块链完整性", command=self.validate_chain)
        self.validate_button.pack(pady=5, fill=X)
        self.tamper_button = ttk.Button(action_frame, text="⚠️篡改演示", command=self.tamper_chain)
        self.tamper_button.pack(pady=5, fill=X)
        self.restore_button = ttk.Button(action_frame, text="↩恢复篡改", command=self.restore_chain)
        self.restore_button.pack(pady=5, fill=X)
        self.export_button = ttk.Button(action_frame, text="📄导出演示报告", command=self.export_report)
        self.export_button.pack(pady=5, fill=X)
        self.signature_demo_button = ttk.Button(action_frame, text="🔎签名示意", command=self.signature_demo)
        self.signature_demo_button.pack(pady=5, fill=X)
        self.multiminer_button = ttk.Button(action_frame, text="👥多矿工模拟", command=self.simulate_multi_mining)
        self.multiminer_button.pack(pady=5, fill=X)
        self.block_detail_button = ttk.Button(action_frame, text="🧩最新区块详情", command=self.show_latest_block)
        self.block_detail_button.pack(pady=5, fill=X)

        ttk.Label(action_frame, text="设置:", font=('Arial', 10, 'bold')).pack(pady=(5, 0))

        self.change_password_button = ttk.Button(action_frame, text="🔒更改密码", command=self.change_password)
        self.change_password_button.pack(pady=5, fill=X)

        self.settings_button = ttk.Button(action_frame, text="⚙设置", command=self.show_settings)
        self.settings_button.pack(pady=5, fill=X)

        self.safe_close_button = ttk.Button(action_frame, text="🛡️安全退出", command=self.safe_close)
        self.safe_close_button.pack(pady=5, fill=X)

        ttk.Separator(action_frame, orient=HORIZONTAL).pack(fill=X, pady=10)

        self.about_button = ttk.Button(action_frame, text="👽关于我们", command=self.about_us)
        self.about_button.pack(pady=5, fill=X)
        self.chain_status_label = ttk.Label(action_frame, text="链状态: 未验证", foreground="gray")
        self.chain_status_label.pack(pady=(5, 0))
        self.difficulty_label = ttk.Label(action_frame,
                                          text=f"当前挖矿难度: {self.blockchain.get_difficulty()} ('0'开头)")
        self.difficulty_label.pack(pady=(10, 0))
        ttk.Label(action_frame, text=f"矿工奖励: {MINING_REWARD} T币").pack(pady=(0, 5))
        ttk.Separator(action_frame, orient=HORIZONTAL).pack(fill=X, pady=10)
        display_container = ttk.Frame(main_frame, padding="5")
        display_container.pack(side=RIGHT, fill=BOTH, expand=True)

        dashboard_frame = ttk.Frame(display_container)
        dashboard_frame.pack(fill=X, pady=(0, 6))
        self.dash_chain_len = ttk.Label(dashboard_frame, text="区块数: 0")
        self.dash_chain_len.pack(side=LEFT, padx=(0, 12))
        self.dash_difficulty = ttk.Label(dashboard_frame, text="难度: 0")
        self.dash_difficulty.pack(side=LEFT, padx=(0, 12))
        self.dash_last_time = ttk.Label(dashboard_frame, text="上一块耗时: -")
        self.dash_last_time.pack(side=LEFT, padx=(0, 12))
        self.dash_avg_time = ttk.Label(dashboard_frame, text="平均出块: -")
        self.dash_avg_time.pack(side=LEFT)

        self.notebook = ttk.Notebook(display_container)
        self.notebook.pack(fill=BOTH, expand=True, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        chain_tab = ttk.Frame(self.notebook)
        self.notebook.add(chain_tab, text='完整区块链')
        visual_tab = ttk.Frame(self.notebook)
        self.notebook.add(visual_tab, text='链可视化')
        self.chain_text = scrolledtext.ScrolledText(chain_tab, wrap=WORD, state=DISABLED, font=self.get_mono_font(9),
                                                    background='#2e2e2e', foreground='#f0f0f0',
                                                    insertbackground='#f0f0f0')
        self.chain_text.pack(fill=BOTH, expand=True)
        visual_header = ttk.Frame(visual_tab)
        visual_header.pack(fill=X, padx=6, pady=(6, 2))
        self.chain_legend_label = ttk.Label(visual_header, text="图例: 创世=蓝色, 有效=绿色, 异常=红色 | 矿工=彩色标记")
        self.chain_legend_label.pack(side=LEFT)
        self.chain_hint_label = ttk.Label(visual_header, text="点击区块查看详情", foreground="#888888")
        self.chain_hint_label.pack(side=RIGHT)
        self.chain_selected_label = ttk.Label(visual_tab, text="选中: 无", anchor=W)
        self.chain_selected_label.pack(fill=X, padx=6, pady=(0, 4))
        visual_container = ttk.Frame(visual_tab)
        visual_container.pack(fill=BOTH, expand=True)
        self.chain_canvas = tk.Canvas(visual_container, bg="#1e1e1e", highlightthickness=0)
        self.chain_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.chain_canvas_scroll_y = ttk.Scrollbar(visual_container, orient="vertical", command=self.chain_canvas.yview)
        self.chain_canvas_scroll_y.pack(side=RIGHT, fill=Y)
        self.chain_canvas_scroll_x = ttk.Scrollbar(visual_tab, orient="horizontal", command=self.chain_canvas.xview)
        self.chain_canvas_scroll_x.pack(fill=X)
        self.chain_canvas.configure(yscrollcommand=self.chain_canvas_scroll_y.set,
                                    xscrollcommand=self.chain_canvas_scroll_x.set)
        self.chain_canvas.bind("<Button-1>", self.on_chain_canvas_click)
        self.canvas_block_rects = {}
        self.selected_block_rect = None

        balance_tab = ttk.Frame(self.notebook)
        self.notebook.add(balance_tab, text='账户余额')
        self.balance_text = scrolledtext.ScrolledText(
            balance_tab,
            wrap=WORD,
            state=DISABLED,
            font=self.get_mono_font(10),
            background='#1e1e1e',
            foreground='#f0f0f0',
            insertbackground='#f0f0f0'
        )
        self.balance_text.pack(fill=BOTH, expand=True)

        pending_tab = ttk.Frame(self.notebook)
        self.notebook.add(pending_tab, text='待处理交易')
        self.pending_text = scrolledtext.ScrolledText(
            pending_tab,
            wrap=WORD,
            state=DISABLED,
            font=self.get_mono_font(10),
            background='#1e1e1e',
            foreground='#f0f0f0',
            insertbackground='#f0f0f0'
        )
        self.pending_text.pack(fill=BOTH, expand=True)

        self.status_bar = ttk.Label(self.root, text="就绪。", relief=SUNKEN, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X)

        self.mining_sensitive_controls = [
            self.set_miner_button,
            self.tx_button,
            self.save_button,
            self.load_button,
            self.validate_button,
            self.tamper_button,
            self.restore_button,
            self.export_button,
            self.signature_demo_button,
            self.multiminer_button,
            self.block_detail_button,
            self.settings_button,
            self.change_password_button,
            self.safe_close_button,
        ]
        self.bind_scroll_events(control_canvas, control_canvas)
        self.bind_scroll_events(self.chain_canvas, self.chain_canvas, allow_x=True)
        self.ui_fonts_ready = True
        self.capture_widget_font_sizes(self.root)
        self.apply_ui_scale(self.ui_scale_var.get())
        self.update_display()

    def detect_ui_scale(self):
        try:
            dpi = self.root.winfo_fpixels('1i')
            if dpi:
                return max(1.0, min(1.35, dpi / 110.0))
        except Exception:
            pass
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        if screen_w >= 3840 or screen_h >= 2160:
            return 1.3
        if screen_w >= 2560:
            return 1.15
        return 1.0

    def get_mono_font(self, size):
        scale = self.ui_scale_var.get() or 1.0
        scaled = max(8, int(size * scale))
        return ('Consolas', scaled)

    def capture_widget_font_sizes(self, widget):
        try:
            font_value = widget.cget("font")
            if font_value:
                fnt = tkfont.Font(root=self.root, font=font_value)
                size = fnt.cget("size")
                if size != 0:
                    self.widget_font_base_sizes[widget] = size
        except Exception:
            pass
        for child in widget.winfo_children():
            self.capture_widget_font_sizes(child)

    def scale_widget_fonts(self, scale):
        for widget, base_size in list(self.widget_font_base_sizes.items()):
            try:
                font_value = widget.cget("font")
            except Exception:
                continue
            if not font_value:
                continue
            try:
                fnt = tkfont.Font(root=self.root, font=font_value)
                sign = -1 if base_size < 0 else 1
                new_size = max(8, int(abs(base_size) * scale)) * sign
                fnt.configure(size=new_size)
                widget.configure(font=fnt)
            except Exception:
                continue

    def apply_ui_scale(self, scale):
        try:
            scale = float(scale)
        except Exception:
            scale = 1.0
        scale = max(0.8, min(2.0, scale))
        self.ui_scale_var.set(scale)
        try:
            self.root.tk.call('tk', 'scaling', scale)
        except Exception:
            pass
        base_size = max(9, int(10 * scale))
        mono_size_9 = max(8, int(9 * scale))
        mono_size_10 = max(9, int(10 * scale))
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(size=base_size)
            tkfont.nametofont("TkTextFont").configure(size=base_size)
            tkfont.nametofont("TkMenuFont").configure(size=base_size)
            tkfont.nametofont("TkHeadingFont").configure(size=base_size)
            tkfont.nametofont("TkFixedFont").configure(size=mono_size_9)
        except Exception:
            pass
        try:
            self.style.configure('TButton', padding=int(6 * scale), font=('Arial', base_size, 'bold'))
            self.style.configure('TLabel', font=('Arial', base_size))
        except Exception:
            pass
        if hasattr(self, "chain_text"):
            self.chain_text.config(font=('Consolas', mono_size_9))
        if hasattr(self, "balance_text"):
            self.balance_text.config(font=('Consolas', mono_size_10))
        if hasattr(self, "pending_text"):
            self.pending_text.config(font=('Consolas', mono_size_10))
        if self.ui_fonts_ready:
            self.scale_widget_fonts(scale)
        if hasattr(self, "chain_canvas"):
            self.draw_chain_visualization()

    @staticmethod
    def mousewheel_units(event):
        if getattr(event, "num", None) == 4:
            return -1
        if getattr(event, "num", None) == 5:
            return 1
        delta = getattr(event, "delta", 0)
        if delta == 0:
            return 0
        step = int(-delta / 120)
        return step if step else (-1 if delta > 0 else 1)

    def bind_scroll_events(self, widget, target, allow_x=False):
        def _scroll_y(event):
            steps = self.mousewheel_units(event)
            if steps:
                target.yview_scroll(steps, "units")
            return "break"

        if allow_x:
            def _scroll_x(event):
                steps = self.mousewheel_units(event)
                if steps:
                    target.xview_scroll(steps, "units")
                return "break"

        def _bind_tree(node):
            node.bind("<MouseWheel>", _scroll_y)
            node.bind("<Button-4>", _scroll_y)
            node.bind("<Button-5>", _scroll_y)
            if allow_x:
                node.bind("<Shift-MouseWheel>", _scroll_x)
            for child in node.winfo_children():
                _bind_tree(child)

        _bind_tree(widget)

    def set_mining_sensitive_controls(self, enabled):
        state = NORMAL if enabled else DISABLED
        entry_state = "normal" if enabled else "disabled"
        for widget in self.mining_sensitive_controls:
            widget.config(state=state)
        self.recipient_entry.config(state=entry_state)
        self.amount_entry.config(state=entry_state)

    def set_single_mining_state(self, busy):
        self.set_mining_sensitive_controls(not busy)
        if busy:
            self.mine_button.config(text="🔥 正在挖矿...", state=DISABLED)
            self.start_cont_mine_button.config(state=DISABLED)
            self.stop_cont_mine_button.config(state=DISABLED)
        else:
            self.mine_button.config(text="单次挖矿 (PoW)", state=NORMAL)
            self.start_cont_mine_button.config(state=NORMAL)
            self.stop_cont_mine_button.config(state=DISABLED)

    def set_continuous_mining_state(self, active):
        self.set_mining_sensitive_controls(not active)
        if active:
            self.mine_button.config(state=DISABLED)
            self.start_cont_mine_button.config(state=DISABLED)
            self.stop_cont_mine_button.config(state=NORMAL)
        else:
            self.mine_button.config(text="单次挖矿 (PoW)", state=NORMAL)
            self.start_cont_mine_button.config(state=NORMAL)
            self.stop_cont_mine_button.config(state=DISABLED)

    def select_notebook_tab(self, title):
        for tab_id in self.notebook.tabs():
            if self.notebook.tab(tab_id, "text") == title:
                self.notebook.select(tab_id)
                return True
        return False

    def set_miner(self):
        new_miner_id = simpledialog.askstring("切换/创建钱包", "请输入钱包名：", parent=self.root)
        if new_miner_id is None:
            return
        new_miner_id = new_miner_id.strip()

        if new_miner_id.upper() == "SYSTEM":
            messagebox.showerror("权限错误", "禁止使用系统保留账户名！")
            self.miner_id_var.set(self.miner_id)
            return

        if not new_miner_id:
            messagebox.showerror("错误", "钱包名不能为空。")
            self.miner_id_var.set(self.miner_id)
            return

        if new_miner_id not in self.blockchain.wallets:
            self.blockchain.register_new_wallet(new_miner_id)
            messagebox.showinfo("钱包创建成功", f"新钱包 '{new_miner_id}' 已创建！")

        self.miner_id = new_miner_id
        self.miner_id_var.set(self.miner_id)
        self.update_status_bar(f"已切换到钱包: {self.miner_id}")
        self.update_display()

    def update_status_bar(self, message):

        self.status_bar.config(text=message)

    def create_transaction(self):
        sender = self.miner_id
        recipient = self.recipient_entry.get().strip()
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("错误", "金额必须是数字。")
            return

        if not sender or not recipient:
            messagebox.showerror("错误", "发送方和接收方不能为空。")
            return

        sender_private_key = self.blockchain.wallets.get(sender)
        if not sender_private_key:
            messagebox.showerror("错误", f"找不到钱包 '{sender}' 的私钥，无法签名。")
            return

        if self.blockchain.new_transaction(sender, recipient, amount, sender_private_key):
            messagebox.showinfo("交易已添加", f"交易已添加：{sender} -> {recipient} ({amount} T币)", parent=self.root)
            self.recipient_entry.delete(0, END)
            self.amount_entry.delete(0, END)
            self.amount_entry.insert(0, "10.0")

            self.select_notebook_tab("待处理交易")
            self.update_display()
        else:
            messagebox.showerror("交易失败", self.blockchain.last_error or "交易提交失败。", parent=self.root)

    def prepare_mining_job(self, miner_id=None):
        last_block = self.blockchain.last_block
        if last_block is None:
            last_proof = 0
            prev_hash = GENESIS_PREV_HASH
        else:
            last_proof = last_block.get('proof', 0)
            prev_hash = last_block.get('hash', GENESIS_PREV_HASH)

        transactions_to_mine = list(self.blockchain.pending_transactions)

        active_miner = miner_id or self.miner_id
        reward_tx_data = {
            'sender': "SYSTEM",
            'recipient': active_miner,
            'amount': MINING_REWARD,
            'timestamp': time.time(),
        }
        reward_signature = Wallet.sign_transaction("SYSTEM_PRIVATE_KEY", reward_tx_data)
        transactions_to_mine.insert(0, {**reward_tx_data, 'signature': reward_signature})

        current_difficulty = self.blockchain.get_difficulty()
        return {
            'last_proof': last_proof,
            'prev_hash': prev_hash,
            'transactions': transactions_to_mine,
            'miner': active_miner,
            'difficulty': current_difficulty,
        }

    def perform_mining_job(self, job_data, max_seconds=None, cancel_event=None, progress_cb=None):
        start_time = time.time()
        proof = self.blockchain.perform_proof_of_work(
            job_data['last_proof'],
            job_data['transactions'],
            job_data['difficulty'],
            max_seconds=max_seconds,
            progress_cb=progress_cb,
            progress_every=self.pow_progress_every,
            cancel_event=cancel_event,
        )
        return proof, time.time() - start_time

    def finalize_mined_block(self, job_data, proof):
        return self.blockchain.mine_block(
            proof,
            job_data['prev_hash'],
            job_data['transactions'],
            job_data['miner'],
        )

    def mine_block_logic(self, max_seconds=None, miner_id=None):
        job_data = self.prepare_mining_job(miner_id)
        proof, elapsed = self.perform_mining_job(job_data, max_seconds=max_seconds)
        block = self.finalize_mined_block(job_data, proof)
        return block, elapsed

    def run_pow_worker(self, token, mode, job_data, max_seconds, cancel_event):
        def progress_cb(attempts, elapsed):
            self.root.after(0, self.on_pow_progress, attempts, elapsed, token)

        try:
            proof, elapsed = self.perform_mining_job(
                job_data,
                max_seconds=max_seconds,
                cancel_event=cancel_event,
                progress_cb=progress_cb,
            )
            self.root.after(0, self.on_pow_worker_success, token, mode, job_data, proof, elapsed)
        except Exception as exc:
            self.root.after(0, self.on_pow_worker_error, token, mode, str(exc))

    def start_pow_worker(self, mode, max_seconds, miner_id=None):
        if self.active_pow_thread and self.active_pow_thread.is_alive():
            return False
        job_data = self.prepare_mining_job(miner_id)
        self.pow_job_token += 1
        token = self.pow_job_token
        self.last_pow_attempts = 0
        self.pow_attempts_label.config(text="尝试次数: 0")
        self.pow_status_label.config(text="PoW状态: 计算中")
        cancel_event = threading.Event()
        worker = threading.Thread(
            target=self.run_pow_worker,
            args=(token, mode, job_data, max_seconds, cancel_event),
            daemon=True,
        )
        self.active_pow_cancel_event = cancel_event
        self.active_pow_thread = worker
        worker.start()
        return True

    def on_pow_worker_success(self, token, mode, job_data, proof, elapsed):
        if token != self.pow_job_token:
            return
        self.active_pow_thread = None
        self.active_pow_cancel_event = None
        self.pow_status_label.config(text="PoW状态: 空闲")
        block = self.finalize_mined_block(job_data, proof)

        if mode == "single":
            self.set_single_mining_state(False)
            self.update_status_bar(f"单次挖矿成功！用时: {elapsed:.2f}s | 区块 #{block['index']}")
            messagebox.showinfo(
                "挖矿成功",
                f"新区块 #{block['index']} 已被挖出！\n用时: {elapsed:.2f}s\n获得 {MINING_REWARD} T币奖励。",
                parent=self.root,
            )
            self.select_notebook_tab("完整区块链")
            self.update_display()
            return

        self.update_status_bar(
            f"⛏️ 持续挖矿中 | 发现新区块 #{block['index']} (用时: {elapsed:.2f}s) | 难度: {self.blockchain.get_difficulty()}"
        )
        self.update_display()
        if self.is_mining_continous:
            self.root.after(self.mining_interval_ms, self.continuous_mining_loop)

    def on_pow_worker_error(self, token, mode, error_message):
        if token != self.pow_job_token:
            return
        self.active_pow_thread = None
        self.active_pow_cancel_event = None
        self.pow_status_label.config(text="PoW状态: 空闲")

        if mode == "single":
            self.set_single_mining_state(False)
            self.update_status_bar(f"单次挖矿失败: {error_message}")
            messagebox.showerror("挖矿失败", f"挖矿过程中发生错误: {error_message}", parent=self.root)
            return

        if "超时" in error_message:
            messagebox.showerror("工作量证明超时", "工作量证明超时，已中止持续挖矿。", parent=self.root)
            self.stop_continuous_mining(silent=True)
        elif "已取消" in error_message:
            self.stop_continuous_mining(silent=True)
        else:
            messagebox.showerror("挖矿错误", f"持续挖矿错误: {error_message}", parent=self.root)
            self.stop_continuous_mining(silent=True)

    def mine_block_single(self):
        self.update_status_bar(f"开始单次挖矿... 当前难度: {self.blockchain.get_difficulty()}")
        self.set_single_mining_state(True)
        if not self.start_pow_worker("single", self.pow_timeout_single_sec):
            self.set_single_mining_state(False)
            messagebox.showwarning("提示", "当前仍有挖矿任务正在进行，请稍候再试。", parent=self.root)

    def start_continuous_mining(self):
        if self.is_mining_continous:
            return

        self.is_mining_continous = True
        self.set_continuous_mining_state(True)
        self.update_status_bar("🚀 持续挖矿模式已启动...")
        self.continuous_mining_loop()

    def stop_continuous_mining(self, silent=False):
        if not self.is_mining_continous:
            return

        self.is_mining_continous = False
        self.pow_job_token += 1
        if self.active_pow_cancel_event:
            self.active_pow_cancel_event.set()
        self.set_continuous_mining_state(False)
        self.pow_status_label.config(text="PoW状态: 空闲")
        self.update_status_bar("🛑 持续挖矿模式已停止。")
        if not silent:
            messagebox.showinfo("挖矿停止", "持续挖矿模式已停止。", parent=self.root)
        self.update_display()

    def continuous_mining_loop(self):
        if not self.is_mining_continous:
            return

        if not self.start_pow_worker("continuous", self.pow_timeout_cont_sec):
            self.root.after(50, self.continuous_mining_loop)

    def save_data(self):
        if self.blockchain.save_chain(BLOCKCHAIN_FILE_PATH):
            messagebox.showinfo("保存成功", f"区块链数据已保存到 {BLOCKCHAIN_FILE_PATH}")
            self.update_status_bar(f"区块链数据已保存到 {BLOCKCHAIN_FILE_PATH}")
        else:
            messagebox.showerror("保存失败", self.blockchain.last_error or "无法保存区块链。", parent=self.root)

    def load_data(self):
        if messagebox.askyesno("加载数据", "这将覆盖当前所有未保存的进度，确定要加载吗？"):
            if self.blockchain.load_chain(BLOCKCHAIN_FILE_PATH):
                messagebox.showinfo("加载成功", f"已从 {BLOCKCHAIN_FILE_PATH} 加载数据。")
                self.update_status_bar(f"已从 {BLOCKCHAIN_FILE_PATH} 加载数据。")
                self.update_display()
            else:
                messagebox.showerror("加载失败", self.blockchain.last_error or "无法加载区块链文件或文件损坏。", parent=self.root)

    def validate_chain(self):
        self.update_status_bar("正在验证区块链完整性...")
        self.root.update_idletasks()
        if self.blockchain.is_chain_valid():
            messagebox.showinfo("验证结果", "✅ 区块链验证通过！完整性良好。")
            self.update_status_bar("验证通过。")
            self.set_chain_status(True)
        else:
            messagebox.showerror("验证结果", f"❌ 区块链验证失败！\n{self.blockchain.last_error}", parent=self.root)
            self.update_status_bar("验证失败。")
            self.set_chain_status(False)

    def tamper_chain(self):
        if len(self.blockchain.chain) <= 1:
            messagebox.showwarning("篡改演示", "链条过短，无法演示篡改。")
            return
        if self.tamper_backup is None:
            self.tamper_backup = copy.deepcopy(self.blockchain.chain)
        target_block = self.blockchain.chain[-1]
        txs = target_block.get('transactions', [])
        if txs:
            first_tx = txs[0]
            if isinstance(first_tx, dict):
                first_tx['amount'] = float(first_tx.get('amount', 0)) + 0.01
            else:
                txs[0] = {"sender": "TAMPER", "recipient": "TAMPER", "amount": 0.01, "timestamp": time.time()}
        else:
            target_block['transactions'] = [{"sender": "TAMPER", "recipient": "TAMPER", "amount": 0.01, "timestamp": time.time()}]
        messagebox.showinfo("篡改演示", "已篡改最新区块的交易数据，验证应当失败。")
        self.set_chain_status(False)
        self.update_display()

    def restore_chain(self):
        if self.tamper_backup is not None:
            self.blockchain.chain = self.tamper_backup
            self.tamper_backup = None
            self.update_display()
            self.set_chain_status(True)
            messagebox.showinfo("恢复完成", "已恢复篡改前的链数据。")
        else:
            if self.blockchain.load_chain(BLOCKCHAIN_FILE_PATH):
                self.update_display()
                self.set_chain_status(True)
                messagebox.showinfo("恢复完成", "已从文件恢复链数据。")
            else:
                messagebox.showwarning("恢复失败", self.blockchain.last_error or "没有备份且文件恢复失败。", parent=self.root)

    def export_report(self):
        now_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        report_path = os.path.join(SCRIPT_DIR, f"tchain_report_{now_str}.txt")
        balances = self.blockchain.get_all_balances()
        top_balances = sorted(balances.items(), key=lambda item: item[1], reverse=True)[:10]
        last_block = self.blockchain.last_block or {}
        lines = [
            "TChain 演示报告",
            f"生成时间: {time.ctime()}",
            f"区块数: {len(self.blockchain.chain)}",
            f"当前难度: {self.blockchain.get_difficulty()}",
            f"待处理交易数: {len(self.blockchain.pending_transactions)}",
            "",
            "余额排行(Top10):",
        ]
        if top_balances:
            for user, bal in top_balances:
                lines.append(f"- {user}: {bal:.2f} T币")
        else:
            lines.append("- 暂无记录")
        lines.extend([
            "",
            "最新区块摘要:",
            f"- index: {last_block.get('index')}",
            f"- hash: {last_block.get('hash')}",
            f"- previous_hash: {last_block.get('previous_hash')}",
            f"- proof: {last_block.get('proof')}",
            f"- transactions: {len(last_block.get('transactions', []))}",
        ])
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        messagebox.showinfo("导出成功", f"报告已保存到:\n{report_path}")

    def signature_demo(self):
        recipient = self.recipient_entry.get().strip() or "Receiver"
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            amount = 1.0
        sender = self.miner_id
        tx_data = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": time.time(),
        }
        tx_string = json.dumps(tx_data, sort_keys=True, ensure_ascii=False, indent=2)
        tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
        private_key = self.blockchain.wallets.get(sender, "")
        signature = Wallet.sign_transaction(private_key, tx_data)
        detail = (
            f"交易数据:\n{tx_string}\n\n"
            f"交易哈希: {tx_hash}\n"
            f"签名结果: {signature}\n"
            f"私钥(片段): {private_key[:12]}...\n"
        )
        messagebox.showinfo("签名示意", detail)

    def simulate_multi_mining(self):
        miners = ["Miner-A", "Miner-B", "Miner-C"]
        for miner in miners:
            if miner not in self.blockchain.wallets:
                self.blockchain.register_new_wallet(miner)
        weights = [random.uniform(0.8, 1.2) for _ in miners]
        winner = random.choices(miners, weights=weights, k=1)[0]
        try:
            block, elapsed = self.mine_block_logic(max_seconds=self.pow_timeout_cont_sec, miner_id=winner)
            messagebox.showinfo(
                "多矿工模拟",
                f"矿工竞争结果: {winner} 领先出块！\n区块 #{block['index']} | 用时 {elapsed:.2f}s"
            )
        except Exception as e:
            messagebox.showerror("多矿工模拟", f"模拟失败: {e}")
        self.update_display()

    def show_latest_block(self):
        if not self.blockchain.chain:
            messagebox.showwarning("区块详情", "当前链为空。")
            return
        self.show_block_detail(self.blockchain.chain[-1].get('index', 1))

    def show_block_detail(self, block_index):
        info = self.get_block_integrity_info(block_index)
        block = info['block']
        detail = (
            f"区块 #{block_index}\n"
            f"时间戳: {time.ctime(block.get('timestamp'))}\n"
            f"哈希: {block.get('hash')}\n"
            f"前一哈希: {block.get('previous_hash')}\n"
            f"证明(Nonce): {block.get('proof')}\n"
            f"矿工: {block.get('miner', '未知')}\n"
            f"难度: {info['difficulty']}\n"
            f"PoW哈希: {info['pow_hash']}\n"
            f"前链校验: {info['prev_link_valid']}\n"
            f"区块哈希校验: {info['hash_valid']}\n"
            f"PoW校验: {info['pow_valid']}\n"
            f"综合状态: {'正常' if info['is_valid'] else '异常'}\n"
            f"交易数: {len(block.get('transactions', []))}\n"
        )
        messagebox.showinfo("区块详情", detail)

    def on_chain_canvas_click(self, event):
        item = self.chain_canvas.find_closest(event.x, event.y)
        if not item:
            return
        tags = self.chain_canvas.gettags(item[0])
        block_index = None
        for tag in tags:
            if tag.startswith("block_"):
                try:
                    block_index = int(tag.split("_", 1)[1])
                except ValueError:
                    block_index = None
                break
        if block_index:
            rect_id = self.canvas_block_rects.get(block_index)
            if rect_id:
                if self.selected_block_rect:
                    self.chain_canvas.itemconfigure(self.selected_block_rect, width=1)
                self.chain_canvas.itemconfigure(rect_id, width=3)
                self.selected_block_rect = rect_id
            info = self.get_block_integrity_info(block_index)
            block = info['block']
            miner_id = block.get('miner', '未知')
            tx_count = len(block.get('transactions', []))
            nonce = block.get('proof', 0)
            self.chain_selected_label.config(
                text=f"选中: 区块 #{block_index} | 矿工 {miner_id} | Tx {tx_count} | 难度 {info['difficulty']} | Nonce {nonce}"
            )
            self.show_block_detail(block_index)

    def get_miner_color(self, miner_id):
        if not miner_id:
            return "#7a7a7a"
        cached = self.miner_color_map.get(miner_id)
        if cached:
            return cached
        digest = hashlib.sha256(miner_id.encode("utf-8")).hexdigest()
        hue = int(digest[:2], 16) / 255.0
        light = 0.42 + (int(digest[2:4], 16) / 255.0) * 0.18
        sat = 0.55 + (int(digest[4:6], 16) / 255.0) * 0.25
        r, g, b = colorsys.hls_to_rgb(hue, light, sat)
        color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        self.miner_color_map[miner_id] = color
        return color

    def get_block_integrity_info(self, block_index):
        block = self.blockchain.chain[block_index - 1]
        block_hash = block.get('hash') or '-'
        expected_hash = self.blockchain.hash_block(block)
        hash_valid = block_hash == expected_hash

        if block_index <= 1:
            difficulty = 0
            pow_hash = "-"
            prev_link_valid = block.get('previous_hash') == GENESIS_PREV_HASH
            pow_valid = True
        else:
            prev_block = self.blockchain.chain[block_index - 2]
            difficulty = self.blockchain.difficulty_at_index(prev_block.get('index', 0))
            transactions_string = json.dumps(block.get('transactions', []), sort_keys=True).encode()
            pow_guess = f"{prev_block.get('proof', 0)}{block.get('proof')}{transactions_string}".encode()
            pow_hash = hashlib.sha256(pow_guess).hexdigest()
            pow_valid = self.blockchain.is_valid_proof(
                prev_block.get('proof', 0),
                block.get('proof'),
                block.get('transactions', []),
                difficulty,
            )
            prev_link_valid = block.get('previous_hash') == self.blockchain.hash_block(prev_block)

        is_valid = prev_link_valid and hash_valid and pow_valid
        return {
            'block': block,
            'difficulty': difficulty,
            'pow_hash': pow_hash,
            'pow_valid': pow_valid,
            'hash_valid': hash_valid,
            'prev_link_valid': prev_link_valid,
            'is_valid': is_valid,
        }

    def draw_chain_visualization(self):
        self.chain_canvas.delete("all")
        self.canvas_block_rects = {}
        self.selected_block_rect = None
        self.chain_selected_label.config(text="选中: 无")
        blocks = self.blockchain.chain
        if not blocks:
            self.chain_canvas.create_text(20, 20, anchor="nw", text="暂无区块", fill="#cccccc")
            return
        scale = self.ui_scale_var.get() or 1.0
        scale = max(0.8, min(2.0, scale))
        width = max(self.chain_canvas.winfo_width(), 900)
        block_w = int(250 * scale)
        block_h = int(150 * scale)
        gap_x = int(30 * scale)
        gap_y = int(60 * scale)
        font_size = max(8, int(9 * scale))
        label_font = ('Consolas', font_size)
        def sy(value):
            return int(value * scale)
        per_row = max(1, (width - gap_x) // (block_w + gap_x))
        for i, block in enumerate(blocks):
            row = i // per_row
            col = i % per_row
            x = gap_x + col * (block_w + gap_x)
            y = gap_y + row * (block_h + gap_y)
            idx = block.get('index', i + 1)
            info = self.get_block_integrity_info(idx)
            miner_id = block.get('miner', '未知')
            miner_color = self.get_miner_color(miner_id)
            if idx <= 1 and info['is_valid']:
                status_color = "#5b8dff"
                fill_color = "#23355f"
                status_text = "创世"
            elif info['is_valid']:
                status_color = "#39b87f"
                fill_color = "#1f3b2f"
                status_text = "有效"
            else:
                status_color = "#e05a5a"
                fill_color = "#3a1f1f"
                status_text = "异常"

            tag = f"block_{idx}"
            block_hash = block.get('hash') or '-'
            rect = self.chain_canvas.create_rectangle(
                x, y, x + block_w, y + block_h,
                fill=fill_color, outline=status_color, width=1, tags=(tag,)
            )
            self.chain_canvas.create_text(x + sy(10), y + sy(8), anchor="nw",
                                          text=f"区块 #{idx}", fill="#ffffff", tags=(tag,), font=label_font)
            self.chain_canvas.create_text(x + sy(10), y + sy(30), anchor="nw",
                                          text=f"状态: {status_text}", fill="#cbd5f5", tags=(tag,), font=label_font)
            self.chain_canvas.create_text(x + sy(10), y + sy(52), anchor="nw",
                                          text=f"Tx: {len(block.get('transactions', []))} | 难度: {info['difficulty']}",
                                          fill="#cbd5f5", tags=(tag,), font=label_font)
            self.chain_canvas.create_text(x + sy(10), y + sy(74), anchor="nw",
                                          text=f"Nonce: {block.get('proof')}", fill="#cbd5f5", tags=(tag,), font=label_font)
            self.chain_canvas.create_text(x + sy(10), y + sy(96), anchor="nw",
                                          text=f"Hash: {block_hash[:10]}...", fill="#9ad1ff", tags=(tag,), font=label_font)
            self.chain_canvas.create_text(x + sy(10), y + sy(118), anchor="nw",
                                          text=f"Prev: {(block.get('previous_hash') or GENESIS_PREV_HASH)[:10]}...", fill="#9ad1ff", tags=(tag,), font=label_font)
            self.chain_canvas.create_text(x + sy(10), y + sy(138), anchor="nw",
                                          text=f"矿工: {miner_id}", fill=miner_color, tags=(tag,), font=label_font)
            self.chain_canvas.create_oval(
                x + block_w - sy(18), y + sy(6), x + block_w - sy(6), y + sy(18),
                fill=miner_color, outline=miner_color, tags=(tag,)
            )
            self.canvas_block_rects[idx] = rect
            if i > 0:
                prev_col = (i - 1) % per_row
                prev_row = (i - 1) // per_row
                px = gap_x + prev_col * (block_w + gap_x) + block_w
                py = gap_y + prev_row * (block_h + gap_y) + block_h / 2
                cx = x
                cy = y + block_h / 2
                self.chain_canvas.create_line(px, py, cx, cy, fill="#6aa6ff", arrow=tk.LAST)
        self.chain_canvas.configure(scrollregion=self.chain_canvas.bbox("all"))

    def on_pow_progress(self, attempts, elapsed, token=None):
        if token is not None and token != self.pow_job_token:
            return
        self.last_pow_attempts = attempts
        self.pow_attempts_label.config(text=f"尝试次数: {attempts}")
        self.pow_status_label.config(text=f"PoW状态: 计算中 ({elapsed:.1f}s)")

    def set_chain_status(self, valid):
        if valid:
            self.chain_status_label.config(text="链状态: ✅ 通过", foreground="green")
        else:
            self.chain_status_label.config(text="链状态: ❌ 异常", foreground="red")

    def about_us(self):
        messagebox.showinfo(
            "关于我们",
            "我是AnonUsAl，一个高中生，是业余编程爱好者。\n"
            "这个程序是我一时兴起所编。\n"
            "如你所见，目前该软件有很多bug。\n"
            "由于bug太多，本人决定开源。\n"
            "我希望结识一群志同道合的朋友们，并帮我们修正他们。\n"
            "本人QQ：3353739856 电报：AnonUsAl\n"
            "我的论坛地址：http://anonusal.tttttttttt.top",
        )

    def show_settings(self):
        setting_window = tk.Toplevel(self.root)
        setting_window.title("设置")
        setting_window.geometry("480x450")
        setting_window.resizable(False, False)

        setting_window.transient(self.root)
        setting_window.grab_set()

        style = ttk.Style()
        style.configure("Red.TButton", foreground="red")

        tabs = ttk.Notebook(setting_window)
        tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        mine_tab = ttk.Frame(tabs, padding=20)
        tabs.add(mine_tab, text=" 挖矿性能 ")

        ttk.Label(mine_tab, text="持续挖矿轮询延迟 (毫秒):", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W)

        delay_scale = tk.Scale(
            mine_tab,
            from_=10,
            to=2000,
            orient=tk.HORIZONTAL,
            variable=self.mining_interval_var,
            tickinterval=490,
            length=350
        )
        delay_scale.pack(pady=10)

        ttk.Label(mine_tab, text="延迟越低，挖矿速度越快，CPU占用越高。", foreground="red").pack(anchor=tk.W)
        ttk.Label(mine_tab, text="单次挖矿超时 (秒):", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, pady=(15, 0))
        single_timeout_scale = tk.Scale(
            mine_tab,
            from_=1,
            to=30,
            orient=tk.HORIZONTAL,
            variable=self.pow_timeout_single_var,
            length=350
        )
        single_timeout_scale.pack(pady=5)

        ttk.Label(mine_tab, text="持续挖矿超时 (秒):", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, pady=(10, 0))
        cont_timeout_scale = tk.Scale(
            mine_tab,
            from_=1,
            to=20,
            orient=tk.HORIZONTAL,
            variable=self.pow_timeout_cont_var,
            length=350
        )
        cont_timeout_scale.pack(pady=5)

        def apply_changes():
            self.mining_interval_ms = self.mining_interval_var.get()
            self.pow_timeout_single_sec = self.pow_timeout_single_var.get()
            self.pow_timeout_cont_sec = self.pow_timeout_cont_var.get()
            self.update_status_bar(
                f"设置已更新：延迟 {self.mining_interval_ms}ms | 单次超时 {self.pow_timeout_single_sec}s | 持续超时 {self.pow_timeout_cont_sec}s"
            )
            messagebox.showinfo("成功", "参数已实时应用！", parent=setting_window)

        ttk.Button(mine_tab, text="应用更改", command=apply_changes).pack(pady=20)

        path_tab = ttk.Frame(tabs, padding=20)
        tabs.add(path_tab, text=" 数据路径 ")

        path_info = [
            ("程序目录:", SCRIPT_DIR),
            ("密码哈希:", Password_hash_file),
            ("区块链库:", BLOCKCHAIN_FILE_PATH),
            ("锁定状态:", LOCK_FILE_PATH),
        ]

        for label, val in path_info:
            ttk.Label(path_tab, text=label, font=('微软雅黑', 9, 'bold')).pack(anchor=tk.W, pady=(5, 0))
            e = ttk.Entry(path_tab)
            e.insert(0, val)
            e.config(state='readonly')
            e.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(path_tab, text="提示: 修改这些文件会导致数据丢失", foreground="gray").pack(pady=10)

        ui_tab = ttk.Frame(tabs, padding=20)
        tabs.add(ui_tab, text=" 界面 ")

        ttk.Label(ui_tab, text="界面缩放 (适配高分辨率):", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, pady=(5, 0))
        scale_slider = tk.Scale(
            ui_tab,
            from_=0.8,
            to=2.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            variable=self.ui_scale_var,
            length=350
        )
        scale_slider.pack(pady=8)
        ttk.Label(ui_tab, text="数值越大，界面字体越大。推荐 4K 使用 1.25~1.35。", foreground="gray").pack(anchor=tk.W)
        ttk.Button(
            ui_tab,
            text="应用缩放",
            command=lambda: self.apply_ui_scale(self.ui_scale_var.get()),
        ).pack(pady=12, anchor=tk.W)

        chain_info_tab = ttk.Frame(tabs, padding=20)
        tabs.add(chain_info_tab, text=" 区块链信息 ")

        ttk.Label(chain_info_tab, text="创世区块状态:", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, pady=(5, 0))
        genesis_status = "✅ 本次启动新建" if self.blockchain.created_genesis else "🔄 从本地文件加载"
        genesis_color = "#008000" if self.blockchain.created_genesis else "#1E90FF"
    
        genesis_label = ttk.Label(chain_info_tab, text=genesis_status, foreground=genesis_color, font=('微软雅黑', 10, 'bold'))
        genesis_label.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(chain_info_tab, text="区块链基本信息:", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(chain_info_tab, text=f"总区块数: {len(self.blockchain.chain)}").pack(anchor=tk.W)
        ttk.Label(chain_info_tab, text=f"待处理交易数: {len(self.blockchain.pending_transactions)}").pack(anchor=tk.W)
        ttk.Label(chain_info_tab, text=f"当前挖矿难度: {self.blockchain.get_difficulty()}").pack(anchor=tk.W)

        def reset_genesis():
            if messagebox.askyesno("警告", "重置创世区块会清空所有区块链数据，确定吗？", parent=setting_window):
                self.blockchain.chain = []
                self.blockchain.pending_transactions = []
                self.blockchain.mine_block(proof=100, previous_hash=GENESIS_PREV_HASH, transactions=[], miner_address="SYSTEM")
                self.blockchain.created_genesis = True
                messagebox.showinfo("成功", "创世区块已重置！", parent=setting_window)
                self.update_display()

        ttk.Button(chain_info_tab, text="重置创世区块", command=reset_genesis, style="Red.TButton").pack(anchor=tk.W, pady=10)

        bottom_frame = ttk.Frame(setting_window)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=10)

        ttk.Button(bottom_frame, text="确定并返回", command=setting_window.destroy).pack(side=tk.RIGHT)
    def change_password(self):
        global PASSWORD, password_error_times
        new_password = simpledialog.askstring("更改密码", "请输入新密码：",
                                              parent=self.root,
                                              show='*')
        if new_password:
            if len(new_password) < 8:
                messagebox.showerror("错误", "新密码至少需要 8 位。")
                return
            try:
                hashed = hashlib.sha256(new_password.encode()).hexdigest()
                with open(Password_hash_file, 'w', encoding='utf-8') as f:
                    f.write(hashed)
                PASSWORD = hashed
                password_error_times = 0
                lockon(False)
                messagebox.showinfo("成功", "密码已成功更改！")
            except Exception as e:
                messagebox.showerror("错误", f"更改密码时出错：{e}")

    def safe_close(self):
        if self.blockchain.save_chain(BLOCKCHAIN_FILE_PATH):
            messagebox.showinfo("保存成功", f"区块链数据已保存到 {BLOCKCHAIN_FILE_PATH}")
            self.update_status_bar(f"区块链数据已保存到 {BLOCKCHAIN_FILE_PATH}")
            sys.exit(0)
        else:
            messagebox.showerror("保存失败", self.blockchain.last_error or "无法保存区块链。", parent=self.root)
            sys.exit(1)

    def on_tab_change(self, event):
        
        self.update_display()

    def update_display(self):
        
        current_tab_name = self.notebook.tab(self.notebook.select(), "text")

        if current_tab_name == '完整区块链':
            self.chain_text.config(state=NORMAL)
            self.chain_text.delete(1.0, END)

            self.chain_text.insert(INSERT, f"--- T币 区块链 (总长: {len(self.blockchain.chain)} 区块) ---\n\n",
                                   "header")

            for block in reversed(self.blockchain.chain):
                block_index = block.get('index', 1)
                info = self.get_block_integrity_info(block_index)

                self.chain_text.insert(INSERT, f"区块 #{block_index} ", "block_index")
                self.chain_text.insert(INSERT, f" (矿工: {block.get('miner')})\n")

                self.chain_text.insert(INSERT, f"  时间戳: {time.ctime(block.get('timestamp'))}\n")
                self.chain_text.insert(INSERT, f"  哈希: {block.get('hash')}\n")
                self.chain_text.insert(INSERT, f"  前一哈希: {block.get('previous_hash')}\n")
                self.chain_text.insert(INSERT, f"  证明(Nonce): {block.get('proof')}\n")

                hash_tag = "valid_hash" if info['is_valid'] else "invalid_hash"
                self.chain_text.insert(INSERT,
                                       f"  综合校验: {info['is_valid']} (难度={info['difficulty']})\n",
                                       hash_tag)
                self.chain_text.insert(INSERT,
                                       f"  前链校验: {info['prev_link_valid']} | 区块哈希校验: {info['hash_valid']} | PoW校验: {info['pow_valid']}\n")
                if block_index > 1:
                    target_prefix = "0" * info['difficulty']
                    self.chain_text.insert(INSERT,
                                           f"  难度规则: 需前缀 {info['difficulty']} 个 0 ({target_prefix})\n")
                    self.chain_text.insert(INSERT,
                                           f"  PoW哈希: {info['pow_hash']}\n")

                self.chain_text.insert(INSERT, "  交易列表:\n", "transaction_header")

                if not block.get('transactions'):
                    self.chain_text.insert(INSERT, "    (无交易)\n")
                for tx in block.get('transactions', []):
                    self.chain_text.insert(INSERT,
                                           f"    - {tx.get('sender')} -> {tx.get('recipient')} ({tx.get('amount', 0):.2f} T币)\n")
                self.chain_text.insert(INSERT, "-" * 60 + "\n\n")

            self.chain_text.tag_config("header", foreground="#4CAF50", font=('Consolas', 11, 'bold'))
            self.chain_text.tag_config("block_index", foreground="#FFD700", font=('Consolas', 10, 'bold'))
            self.chain_text.tag_config("valid_hash", foreground="#00FF00")
            self.chain_text.tag_config("invalid_hash", foreground="#FF0000", font=('Consolas', 10, 'bold'))
            self.chain_text.tag_config("transaction_header", foreground="#ADD8E6")
            self.chain_text.config(state=DISABLED)

        elif current_tab_name == '账户余额':
            self.balance_text.config(state=NORMAL)
            self.balance_text.delete(1.0, END)

            self.balance_text.insert(INSERT, "--- T币 账户余额 (基于交易历史计算) ---\n\n", "header")
            self.balance_text.tag_config("header", font=('Consolas', 10, 'bold'), foreground="#FFA500")
            self.balance_text.tag_config("user_name", font=('Consolas', 10, 'bold'))
            self.balance_text.tag_config("balance_positive", foreground="#008000", font=('Consolas', 10, 'bold'))
            self.balance_text.tag_config("balance_negative", foreground="#FF0000", font=('Consolas', 10, 'bold'))
            balances = self.blockchain.get_all_balances()

            if not balances:
                self.balance_text.insert(INSERT, "(暂无交易记录)")
            else:
                sorted_balances = sorted(balances.items(), key=lambda item: item[1], reverse=True)
                for user, balance in sorted_balances:
                    self.balance_text.insert(INSERT, f"{user.ljust(20)}: ", "user_name")
                    balance_tag = "balance_positive" if balance >= 0 else "balance_negative"
                    self.balance_text.insert(INSERT, f"{balance:.2f} T币\n", balance_tag)

            self.balance_text.config(state=DISABLED)

        elif current_tab_name == '待处理交易':
            self.pending_text.config(state=NORMAL)
            self.pending_text.delete(1.0, END)

            self.pending_text.insert(INSERT, "--- 待处理 (待打包) 交易 ---\n\n", "header")

            if not self.blockchain.pending_transactions:
                self.pending_text.insert(INSERT, "(暂无待处理交易)")
            else:
                for tx in self.blockchain.pending_transactions:
                    self.pending_text.insert(INSERT, f"时间: {time.ctime(tx.get('timestamp'))}\n", "time")
                    self.pending_text.insert(INSERT,
                                             f"- {tx.get('sender')} -> {tx.get('recipient')} ({tx.get('amount', 0):.2f} T币)\n",
                                             "tx_detail")
                    signature = tx.get('signature', '')
                    self.pending_text.insert(INSERT, f"  签名: {signature}\n\n", "signature")

            self.pending_text.tag_config("header", font=('Consolas', 10, 'bold'), foreground="#FFA500")
            self.pending_text.tag_config("time", foreground="#808080")
            self.pending_text.tag_config("tx_detail", font=('Consolas', 10, 'bold'))
            self.pending_text.config(state=DISABLED)

        current_balance = self.blockchain.get_balance(self.miner_id)
        current_difficulty = self.blockchain.get_difficulty()
        self.difficulty_label.config(text=f"当前挖矿难度: {current_difficulty} ('0'开头)")
        self.public_key_label.config(text=self.blockchain.addresses.get(self.miner_id, "-"))
        self.private_key_label.config(text=self.blockchain.wallets.get(self.miner_id, "-"))
        self.dash_chain_len.config(text=f"区块数: {len(self.blockchain.chain)}")
        self.dash_difficulty.config(text=f"难度: {current_difficulty}")
        self.draw_chain_visualization()

        if len(self.blockchain.chain) > 1:
            times = [b.get('timestamp', 0) for b in self.blockchain.chain]
            diffs = [t2 - t1 for t1, t2 in zip(times[:-1], times[1:]) if t2 >= t1]
            if diffs:
                avg_time = sum(diffs[-10:]) / min(len(diffs), 10)
                last_time = diffs[-1]
                self.dash_last_time.config(text=f"上一块耗时: {last_time:.2f}s")
                self.dash_avg_time.config(text=f"平均出块: {avg_time:.2f}s")
            else:
                self.dash_last_time.config(text="上一块耗时: -")
                self.dash_avg_time.config(text="平均出块: -")
        else:
            self.dash_last_time.config(text="上一块耗时: -")
            self.dash_avg_time.config(text="平均出块: -")

        self.set_chain_status(self.blockchain.is_chain_valid_silent())

        if self.is_mining_continous:
            self.update_status_bar(
                f"⛏️ 持续挖矿中... | 钱包: {self.miner_id} | 余额: {current_balance:.2f} T币 | 待处理交易: {len(self.blockchain.pending_transactions)}")
        else:
            self.update_status_bar(
                f"就绪。| 钱包: {self.miner_id} | 余额: {current_balance:.2f} T币 | 待处理交易: {len(self.blockchain.pending_transactions)}")

if __name__ == "__main__":
    start_app()
