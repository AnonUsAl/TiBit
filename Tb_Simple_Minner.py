import hashlib
import json
import time
import random
from tkinter import *
import tkinter
from tkinter import messagebox, scrolledtext, ttk
from collections import OrderedDict
import tkinter as tk
import ctypes
import os
import sys
from tkinter import simpledialog
import turtle
# --- 常量定义 ---
MINING_DIFFICULTY = 1  # 增加难度到 1
MINING_REWARD = 5      # 增加奖励
GENESIS_PREV_HASH = "0" * 64
BLOCKCHAIN_FILENAME = "improved_tcoin_chain.json"
password_error_times = 0
lockon = False

# 密码文件设置

SCRIPT_DIR = os.getcwd()
Password_hash_file = os.path.join(SCRIPT_DIR, "password_hash.txt")
DEFAULT_PASSWORD = "12345678"

def alert(title, message):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()


def load_password():
    try:
        if os.path.exists(Password_hash_file):
            with open(Password_hash_file, 'r', encoding='utf-8') as f:
                p = f.read().strip()
                return p if p else hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest()
        else:
            # store hash of default password
            hashed = hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest()
            with open(Password_hash_file, 'w', encoding='utf-8') as f:
                f.write(hashed)
            return hashed
    except Exception:
        return hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest()

def ask_choice(title, message):
    root = tk.Tk()
    root.withdraw()
    result = messagebox.askyesno(title, message)
    root.destroy()
    return result


def password_recover():
    """
    重置密码并解锁，随后重启程序。
    """
    # 显式初始化，确保在 except 块中也能访问到变量
    temp_root = tk.Tk()
    temp_root.withdraw()

    try:
        if messagebox.askyesno("安全验证", "是否重置密码并解除锁定？", parent=temp_root):
            word = simpledialog.askstring("重置密码", "请输入新密码:", show='*', parent=temp_root)

            if word and len(word) >= 8:
                sha256_value = hashlib.sha256(word.encode()).hexdigest()

                # 1. 写入新密码
                with open(Password_hash_file, "w", encoding='utf-8') as file:
                    file.write(sha256_value)

                # 2. 解除锁定状态
                lockon(False)

                messagebox.showinfo("成功", "密码已重置，程序将立即重启。", parent=temp_root)

                # 3. 执行重启逻辑
                temp_root.destroy()
                python = sys.executable
                os.execl(python, python, *sys.argv)
            else:
                messagebox.showwarning("提示", "密码过短或取消操作。是否重新设定？", parent=temp_root)
                lockon(1)
                password_recover()
        else:
            sys.exit()

    except Exception as e:
        messagebox.showerror("错误", f"保存密码失败: {e}", parent=temp_root)
        sys.exit()


PASSWORD = load_password()

def lockon(status):
    with open("lockon.txt", "w") as file:
        file.write(str(status))


def check_lockon():
    try:
        with open("lockon.txt", "r") as file:
            tf = file.read(1)
            if tf == "1":
                return True
            else:
                return False

    except FileNotFoundError:
        return False





def check_password(parent=None, max_attempts=3):
    """弹出密码对话，最多尝试 max_attempts 次。返回 True/False。"""
    global password_error_times
    created_temp_root = False
    dialog_parent = parent
    if dialog_parent is None:
        dialog_parent = tk._default_root
        if dialog_parent is None:
            dialog_parent = Tk()
            dialog_parent.withdraw()
            created_temp_root = True

    try:
        for attempt in range(max_attempts):
            ans = simpledialog.askstring("密码验证", "请输入密码:", show='*', parent=dialog_parent)
            if ans is None:
                break
            ans_hash = hashlib.sha256(ans.encode()).hexdigest()
            if ans_hash == PASSWORD:
                return True
            password_error_times += 1
            messagebox.showerror("错误", f"密码错误 ({password_error_times}/{max_attempts})", parent=dialog_parent)
            if password_error_times >= max_attempts:
                messagebox.showwarning("警告", "密码输入错误次数过多，程序将退出。", parent=dialog_parent)
                lockon(1)
                password_recover()
                pass
    finally:
        if created_temp_root:
            try:
                dialog_parent.destroy()
            except Exception:
                pass
    return False




def start_app():
    root = Tk()
    root.withdraw()
    ok = check_password(parent=root)
    if not ok:
        messagebox.showerror("错误", "密码验证失败，程序退出。", parent=root)
        try:
            root.destroy()
        except Exception:
            pass
        sys.exit(1)

    try:
        tcoin = Blockchain()
        if getattr(tcoin, "created_genesis", False):
            messagebox.showinfo("提示", "未找到本地区块链文件，已为您创建区块链文件", parent=root)
        app = BlockchainApp(root, tcoin)
        root.deiconify()
        root.mainloop()
    except Exception as e:
        messagebox.showerror("程序错误", f"程序运行出错: {e}", parent=root)
        try:
            tcoin.save_chain(BLOCKCHAIN_FILENAME)
        except Exception:
            pass



def full_launch():

        start_app()


class Wallet:
    @staticmethod
    def generate_key_pair():
        private_key = hashlib.sha256(str(time.time() + random.random()).encode()).hexdigest()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()[:40]  # 截断作为地址
        return public_key, private_key

    @staticmethod
    def sign_transaction(private_key, transaction_data):
        """使用私钥对交易数据进行签名（简化）。"""
        tx_string = json.dumps(transaction_data, sort_keys=True)
        signature = hashlib.sha256((tx_string + private_key).encode()).hexdigest()
        return signature

    @staticmethod
    def verify_signature(public_key, signature, transaction_data):
        """验证签名是否有效（简化）。"""
        if transaction_data.get('sender') == "SYSTEM":
            return True
        return len(signature) == 64 and public_key is not None
    



class Blockchain:
    def __init__(self):
        self.pending_transactions = []
        self.chain = []
        default_pub, default_priv = Wallet.generate_key_pair()
        self.wallets = {"AnonUsAl": default_priv}
        self.addresses = {"AnonUsAl": default_pub}

        loaded = self.load_chain(BLOCKCHAIN_FILENAME)
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


    @staticmethod
    def _is_chain_valid_static(chain):
        if not chain:
            return False
        if chain[0].get('previous_hash') != GENESIS_PREV_HASH:
            return False

        for i in range(1, len(chain)):
            current_block = chain[i]
            prev_block = chain[i - 1]

            # 验证前序哈希
            block_copy = {k: v for k, v in prev_block.items() if k != 'hash'}
            expected_prev_hash = hashlib.sha256(json.dumps(OrderedDict(sorted(block_copy.items())), sort_keys=True).encode()).hexdigest()
            if current_block.get('previous_hash') != expected_prev_hash:
                return False

            # 验证 proof
            last_proof = prev_block.get('proof', 0)
            current_proof = current_block.get('proof')
            transactions_to_verify = current_block.get('transactions', [])
            difficulty = MINING_DIFFICULTY + ((prev_block.get('index', 0) // 10))
            difficulty = min(difficulty, 8)
            transactions_string = json.dumps(transactions_to_verify, sort_keys=True).encode()
            guess = f'{last_proof}{current_proof}{transactions_string}'.encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if guess_hash[:difficulty] != '0' * difficulty:
                return False

            # 验证区块自带 ha
            block_copy = {k: v for k, v in current_block.items() if k != 'hash'}
            expected_hash = hashlib.sha256(json.dumps(OrderedDict(sorted(block_copy.items())), sort_keys=True).encode()).hexdigest()
            if current_block.get('hash') != expected_hash:
                return False

        return True

   


    def register_new_wallet(self, user_alias):
        public_key, private_key = Wallet.generate_key_pair()
        self.wallets[user_alias] = private_key
        self.addresses[user_alias] = public_key
        return public_key

    def new_transaction(self, sender, recipient, amount, sender_private_key=None):
        """
        创建一个新交易，并将其添加到待处理交易列表中
        """
        try:
            amount = float(amount)
        except ValueError:
            messagebox.showwarning("警告", "交易失败：金额必须是数字。")
            return False

        if amount <= 0:
            messagebox.showwarning("警告", f"交易失败：金额 {amount} 必须是正数。")
            
            return False

        # 1. 检查余额 (除了 SYSTEM 账户)
        if sender != "SYSTEM":
            if self.get_balance(sender) < amount:
                messagebox.showerror("错误", f"交易失败：{sender} 余额不足。")
               
                return False

            # 2. 模拟签名
            if sender_private_key is None:
                messagebox.showerror("错误", "交易失败：用户交易需要私钥进行签名。")
                
                return False

        transaction_data = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'timestamp': time.time(),
        }

        # 3. 生成签名（简化）
        signature = Wallet.sign_transaction(sender_private_key or "", transaction_data)
        transaction = {**transaction_data, 'signature': signature}

        self.pending_transactions.append(transaction)
        messagebox.showinfo("交易已添加", f"交易已添加：{sender} -> {recipient} ({amount} T币)")

        return True

    def mine_block(self, proof, previous_hash, transactions, miner_address):
        """
        创建并添加一个新区块到链上
        """
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

    def perform_proof_of_work(self, last_proof, transactions, difficulty):
        """
        工作量证明：找到一个 proof，使得哈希以 difficulty 个 '0' 开头
        """
        proof = 0
        while not self.is_valid_proof(last_proof, proof, transactions, difficulty):
            proof += 1
        return proof

    @staticmethod
    def is_valid_proof(last_proof, proof, transactions, difficulty):
        """
        验证证明是否有效
        """
        transactions_string = json.dumps(transactions, sort_keys=True).encode()
        guess = f'{last_proof}{proof}{transactions_string}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == '0' * difficulty

    def difficulty_at_index(self, index):
        """返回给定区块索引处的难度（index 从 1 开始）。"""
        base = MINING_DIFFICULTY
        adjust = (index // 10)
        return min(base + adjust, 8)

    def get_difficulty(self):
        """当前链末尾的难度"""
        return self.difficulty_at_index(len(self.chain))

    def get_balance(self, user):
        """
        计算并返回指定用户的余额
        """
        balance = 0
        for block in self.chain:
            for tx in block.get('transactions', []):
                if tx.get('sender') == user:
                    balance -= tx.get('amount', 0)
                if tx.get('recipient') == user:
                    balance += tx.get('amount', 0)
        return balance

    def get_all_balances(self):
        """获取所有参与过的用户的余额"""
        balances = {}
        for block in self.chain:
            for tx in block.get('transactions', []):
                balances[tx['sender']] = balances.get(tx['sender'], 0) - tx['amount']
                balances[tx['recipient']] = balances.get(tx['recipient'], 0) + tx['amount']

        if "SYSTEM" in balances:
            del balances["SYSTEM"]

        return balances

    def is_chain_valid(self):
        """
        检查整个区块链是否有效（防篡改），包含工作量证明的重新验证
        """
        if not self.chain:
            return True

        genesis = self.chain[0]
        if genesis.get('previous_hash') != GENESIS_PREV_HASH:
            messagebox.showerror("链校验失败", "创世区块的 previous_hash 不正确。", parent=tk._default_root)
            return False

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            prev_block = self.chain[i - 1]

            expected_prev_hash = self.hash_block(prev_block)
            if current_block.get('previous_hash') != expected_prev_hash:
                messagebox.showerror("链校验失败", f"链条断裂：区块 {i} 的 previous_hash 与 区块 {i-1} 的哈希不符。", parent=tk._default_root)
                return False

            last_proof = prev_block.get('proof', 0)
            transactions_to_verify = current_block.get('transactions', [])
            current_difficulty = self.difficulty_at_index(prev_block.get('index', 0))
            if not self.is_valid_proof(last_proof, current_block.get('proof'), transactions_to_verify, current_difficulty):
                messagebox.showerror("链校验失败", f"区块 {i} 的工作量证明无效（Nonce={current_block.get('proof')}，难度={current_difficulty}）。", parent=tk._default_root)
                return False

            expected_hash = self.hash_block(current_block)
            if current_block.get('hash') != expected_hash:
                messagebox.showerror("链校验失败", f"区块 {i} 的哈希值不正确。期望 {expected_hash}，但区块中为 {current_block.get('hash')}", parent=tk._default_root)
                return False

        return True

    def save_chain(self, filename):
        
        try:
            data = {
                'chain': self.chain,
                'pending_transactions': self.pending_transactions,
                'wallets': self.wallets
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("保存失败", f"保存失败: {e}", parent=tk._default_root)
            return False

    def load_chain(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.chain = data.get('chain', [])
                self.pending_transactions = data.get('pending_transactions', [])
                self.wallets = data.get('wallets', {"AnonUsAl": "mock_private_key_001"})

            if not self.is_chain_valid():
                messagebox.showwarning("加载警告", "警告：加载的区块链验证失败！", parent=tk._default_root)

            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            messagebox.showerror("加载失败", f"加载失败: {e}", parent=tk._default_root)
            return False


class BlockchainApp:
    def __init__(self, root, blockchain):
        self.blockchain = blockchain
        self.root = root
        self.root.title("TChain Studio")  # 窗口标题
        self.root.geometry("1440x920")  # 固定窗口大小

        # DPI 适配（Windows）
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        self.is_mining_continous = False
        self.mining_interval_ms = 100  # 持续挖矿时，每次循环检查的间隔（毫秒）

        # 矿工身份（使用默认钱包）
        self.miner_id = "AnonUsAl"
        if self.miner_id not in self.blockchain.wallets:
            self.blockchain.register_new_wallet(self.miner_id)

        # 样式设置
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0')
        style.configure('TButton', padding=6, font=('Arial', 10, 'bold'))
        style.map('TButton', foreground=[('active', 'blue'), ('pressed', 'red')])

        # --- 主容器 ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)

        # --- 控制区 (左侧) ---
        control_frame = ttk.Frame(main_frame, padding="5", relief=GROOVE)
        control_frame.pack(side=LEFT, fill=Y, padx=10)

        # 钱包信息
        wallet_frame = ttk.LabelFrame(control_frame, text=f"当前矿工/发送方 ({self.miner_id})", padding="10")
        wallet_frame.pack(pady=10, fill=X)
        ttk.Label(wallet_frame, text="身份/钱包名:", font=('Arial', 10, 'bold')).pack(side=LEFT, padx=5)
        self.miner_id_var = StringVar(value=self.miner_id)
        self.miner_id_entry = ttk.Entry(wallet_frame, textvariable=self.miner_id_var, width=15)
        self.miner_id_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.set_miner_button = ttk.Button(wallet_frame, text="切换/创建钱包", command=self.set_miner, width=15)
        self.set_miner_button.pack(side=LEFT)

        # 转账交易
        tx_frame = ttk.LabelFrame(control_frame, text="创建交易 (需私钥签名)", padding="10")
        tx_frame.pack(pady=10, fill=X)

        ttk.Label(tx_frame, text="接收方:", width=10).grid(row=0, column=0, sticky=W, pady=2)
        self.recipient_entry = ttk.Entry(tx_frame)
        self.recipient_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.recipient_entry.insert(0, "Bob")

        ttk.Label(tx_frame, text="金额:", width=10).grid(row=1, column=0, sticky=W, pady=2)
        self.amount_entry = ttk.Entry(tx_frame)
        self.amount_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.amount_entry.insert(0, "10.0")

        self.tx_button = ttk.Button(tx_frame, text="提交交易 (签名)", command=self.create_transaction)
        self.tx_button.grid(row=2, columnspan=2, pady=10, sticky="ew")

        tx_frame.grid_columnconfigure(1, weight=1)

        # 挖矿和存取
        action_frame = ttk.LabelFrame(control_frame, text="核心操作", padding="10")
        action_frame.pack(pady=10, fill=X)

        ttk.Label(action_frame, text="挖矿模式:", font=('Arial', 10, 'bold')).pack(pady=(5, 0))

        self.mine_button = ttk.Button(action_frame, text="✈单次挖矿 (PoW)", command=self.mine_block_single)
        self.mine_button.pack(pady=5, fill=X)

        self.start_cont_mine_button = ttk.Button(action_frame, text="🚀 开始持续挖矿", command=self.start_continuous_mining)
        self.start_cont_mine_button.pack(pady=5, fill=X)

        self.stop_cont_mine_button = ttk.Button(action_frame, text="🛑 停止持续挖矿", command=self.stop_continuous_mining, state=DISABLED)
        self.stop_cont_mine_button.pack(pady=5, fill=X)

        ttk.Separator(action_frame, orient=HORIZONTAL).pack(fill=X, pady=10)

        # 存取和验证
        self.save_button = ttk.Button(action_frame, text="💾保存区块链 (.json)", command=self.save_data)
        self.save_button.pack(pady=5, fill=X)

        self.load_button = ttk.Button(action_frame, text="💽加载区块链 (.json)", command=self.load_data)
        self.load_button.pack(pady=5, fill=X)

        self.validate_button = ttk.Button(action_frame, text="🔗验证区块链完整性", command=self.validate_chain)
        self.validate_button.pack(pady=5, fill=X)

        self.about_us = ttk.Button(action_frame, text="👽关于我们", command=self.about_us)
        self.about_us.pack(pady=5, fill=X)

        self.change_password_button = ttk.Button(action_frame, text="🔒更改密码", command=self.change_password)
        self.change_password_button.pack(pady=5, fill=X)

        self.safe_close_button = ttk.Button(action_frame, text="🛡️安全退出", command=self.safe_close)
        self.safe_close_button.pack(pady=5, fill=X)

        # 难度显示
        self.difficulty_label = ttk.Label(action_frame, text=f"当前挖矿难度: {self.blockchain.get_difficulty()} ('0'开头)")
        self.difficulty_label.pack(pady=(10, 0))
        ttk.Label(action_frame, text=f"矿工奖励: {MINING_REWARD} T币").pack(pady=(0, 5))

        # --- 显示区 (右侧 - 使用 Notebook 实现 Tab) ---
        display_container = ttk.Frame(main_frame, padding="5")
        display_container.pack(side=RIGHT, fill=BOTH, expand=True)

        self.notebook = ttk.Notebook(display_container)
        self.notebook.pack(fill=BOTH, expand=True, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # 1. 区块链 Tab
        chain_tab = ttk.Frame(self.notebook)
        self.notebook.add(chain_tab, text='完整区块链')
        self.chain_text = scrolledtext.ScrolledText(chain_tab, wrap=WORD, state=DISABLED, font=('Consolas', 9),
                                                    background='#2e2e2e', foreground='#f0f0f0', insertbackground='#f0f0f0')
        self.chain_text.pack(fill=BOTH, expand=True)

        # 2. 余额 Tab
        balance_tab = ttk.Frame(self.notebook)
        self.notebook.add(balance_tab, text='账户余额')
        self.balance_text = scrolledtext.ScrolledText(balance_tab, wrap=WORD, state=DISABLED, font=('Consolas', 10))
        self.balance_text.pack(fill=BOTH, expand=True)

        # 3. 待处理 Tab
        pending_tab = ttk.Frame(self.notebook)
        self.notebook.add(pending_tab, text='待处理交易')
        self.pending_text = scrolledtext.ScrolledText(pending_tab, wrap=WORD, state=DISABLED, font=('Consolas', 10))
        self.pending_text.pack(fill=BOTH, expand=True)

        # --- 状态栏 ---
        self.status_bar = ttk.Label(self.root, text="就绪。", relief=SUNKEN, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X)

        # 初始显示
        self.update_display()

    def set_miner(self):
        """切换当前操作的矿工/发送方钱包"""
        new_miner_id = self.miner_id_var.get().strip()
        if not new_miner_id:
            messagebox.showerror("错误", "钱包名不能为空。")
            self.miner_id_var.set(self.miner_id)  # 恢复原值
            return

        if new_miner_id not in self.blockchain.wallets:
            address = self.blockchain.register_new_wallet(new_miner_id)
            messagebox.showinfo("钱包创建成功", f"新钱包 '{new_miner_id}' 已创建！\n地址: {address}\n(私钥已存储，仅用于本模拟)")

        self.miner_id = new_miner_id
        self.update_status_bar(f"已切换到钱包: {self.miner_id} | 余额: {self.blockchain.get_balance(self.miner_id):.2f} T币")
        self.update_display()

    def update_status_bar(self, message):
        """更新状态栏信息"""
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

        # 获取私钥（模拟）
        sender_private_key = self.blockchain.wallets.get(sender)
        if not sender_private_key:
            messagebox.showerror("错误", f"找不到钱包 '{sender}' 的私钥，无法签名。")
            return

        if self.blockchain.new_transaction(sender, recipient, amount, sender_private_key):
            #messagebox.showinfo("成功", "交易已添加到待处理列表。")
            self.recipient_entry.delete(0, END)
            self.amount_entry.delete(0, END)
            self.amount_entry.insert(0, "10.0")

            self.notebook.select(self.notebook.tabs()[2])  # 切换到待处理交易视图
            self.update_display()

    def mine_block_logic(self):
        """核心挖矿逻辑，供单次和持续挖矿调用"""
        last_block = self.blockchain.last_block
        if last_block is None:
            last_proof = 0
            prev_hash = GENESIS_PREV_HASH
        else:
            last_proof = last_block.get('proof', 0)
            prev_hash = last_block.get('hash', GENESIS_PREV_HASH)

        transactions_to_mine = list(self.blockchain.pending_transactions)

        # 添加挖矿奖励交易
        reward_tx_data = {
            'sender': "SYSTEM",
            'recipient': self.miner_id,
            'amount': MINING_REWARD,
            'timestamp': time.time(),
        }
        reward_signature = Wallet.sign_transaction("SYSTEM_PRIVATE_KEY", reward_tx_data)
        transactions_to_mine.insert(0, {**reward_tx_data, 'signature': reward_signature})

        current_difficulty = self.blockchain.get_difficulty()

        start_time = time.time()
        proof = self.blockchain.perform_proof_of_work(last_proof, transactions_to_mine, current_difficulty)
        elapsed = time.time() - start_time

        # 清空待处理交易并创建新区块
        self.blockchain.pending_transactions = []
        block = self.blockchain.mine_block(proof, prev_hash, transactions_to_mine, self.miner_id)

        return block, elapsed

    def mine_block_single(self):
        """单次挖矿按钮的响应函数"""
        self.mine_button.config(text="🔥 正在挖矿...", state=DISABLED)
        self.root.update_idletasks()  # 强制更新UI

        self.update_status_bar(f"开始单次挖矿... 当前难度: {self.blockchain.get_difficulty()}")

        try:
            block, elapsed = self.mine_block_logic()

            self.update_status_bar(f"单次挖矿成功！用时: {elapsed:.2f}s | 区块 #{block['index']}")
            messagebox.showinfo("挖矿成功", f"新区块 #{block['index']} 已被挖出！\n用时: {elapsed:.2f}s\n获得 {MINING_REWARD} T币奖励。")

            self.notebook.select(self.notebook.tabs()[0])
            self.update_display()

        except Exception as e:
            messagebox.showerror("挖矿失败", f"挖矿过程中发生错误: {e}")
        finally:
            self.mine_button.config(text="单次挖矿 (PoW)", state=NORMAL)

    # --- 持续挖矿功能 ---
    def start_continuous_mining(self):
        """启动持续挖矿模式"""
        if self.is_mining_continous:
            return

        self.is_mining_continous = True
        self.start_cont_mine_button.config(state=DISABLED)
        self.stop_cont_mine_button.config(state=NORMAL)
        self.mine_button.config(state=DISABLED)  # 禁用单次挖矿

        self.update_status_bar("🚀 持续挖矿模式已启动...")
        self.continuous_mining_loop()

    def stop_continuous_mining(self):
        """停止持续挖矿模式"""
        if not self.is_mining_continous:
            return

        self.is_mining_continous = False
        self.start_cont_mine_button.config(state=NORMAL)
        self.stop_cont_mine_button.config(state=DISABLED)
        self.mine_button.config(state=NORMAL)  # 恢复单次挖矿

        self.update_status_bar("🛑 持续挖矿模式已停止。")
        messagebox.showinfo("挖矿停止", "持续挖矿模式已停止。")
        self.update_display()

    def continuous_mining_loop(self):
        """持续挖矿的递归循环函数"""
        if not self.is_mining_continous:
            return

        try:
            block, elapsed = self.mine_block_logic()
            self.update_status_bar(
                f"⛏️ 持续挖矿中 | 发现新区块 #{block['index']} (用时: {elapsed:.2f}s) | 难度: {self.blockchain.get_difficulty()}"
            )
            self.update_display()
        except Exception as e:
            messagebox.showerror("挖矿错误", f"持续挖矿错误: {e}", parent=self.root)
            self.stop_continuous_mining()
            messagebox.showerror("持续挖矿错误", f"持续挖矿过程中发生错误并已停止: {e}")
            return

        self.root.after(self.mining_interval_ms, self.continuous_mining_loop)

    def save_data(self):
        if self.blockchain.save_chain(BLOCKCHAIN_FILENAME):
            messagebox.showinfo("保存成功", f"区块链数据已保存到 {BLOCKCHAIN_FILENAME}")
            self.update_status_bar(f"区块链数据已保存到 {BLOCKCHAIN_FILENAME}")
        else:
            messagebox.showerror("保存失败", "无法保存区块链。")

    def load_data(self):
        if messagebox.askyesno("加载数据", "这将覆盖当前所有未保存的进度，确定要加载吗？"):
            if self.blockchain.load_chain(BLOCKCHAIN_FILENAME):
                messagebox.showinfo("加载成功", f"已从 {BLOCKCHAIN_FILENAME} 加载数据。")
                self.update_status_bar(f"已从 {BLOCKCHAIN_FILENAME} 加载数据。")
                self.update_display()
            else:
                messagebox.showerror("加载失败", "无法加载区块链文件或文件损坏。")

    def validate_chain(self):
        self.update_status_bar("正在验证区块链完整性...")
        self.root.update_idletasks()
        if self.blockchain.is_chain_valid():
            messagebox.showinfo("验证结果", "✅ 区块链验证通过！完整性良好。")
            self.update_status_bar("验证通过。")
        else:
            messagebox.showerror("验证结果", "❌ 区块链验证失败！链条可能已被篡改。")
            self.update_status_bar("验证失败。")

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
    def change_password(self):
        new_password = simpledialog.askstring("更改密码", "请输入新密码：",
                                                    parent=self.root,
                                                    show='*')
        if new_password:
            try:
                hashed = hashlib.sha256(new_password.encode()).hexdigest()
                with open(Password_hash_file, 'w', encoding='utf-8') as f:
                    f.write(hashed)
                messagebox.showinfo("成功", "密码已成功更改！")
            except Exception as e:
                messagebox.showerror("错误", f"更改密码时出错：{e}")
    
    def safe_close(self):
        if self.blockchain.save_chain(BLOCKCHAIN_FILENAME):
            messagebox.showinfo("保存成功", f"区块链数据已保存到 {BLOCKCHAIN_FILENAME}")
            self.update_status_bar(f"区块链数据已保存到 {BLOCKCHAIN_FILENAME}")
            sys.exit(0)
        else:
            messagebox.showerror("保存失败", "无法保存区块链。")
            sys.exit(1)
            
   
        
    def on_tab_change(self, event):
        """当 Tab 改变时触发更新显示"""
        self.update_display()

    def update_display(self):
        """更新所有文本框显示的内容"""
        current_tab_name = self.notebook.tab(self.notebook.select(), "text")

        # 1. 完整区块链 (Chain Tab)
        if current_tab_name == '完整区块链':
            self.chain_text.config(state=NORMAL)
            self.chain_text.delete(1.0, END)

            self.chain_text.insert(INSERT, f"--- T币 区块链 (总长: {len(self.blockchain.chain)} 区块) ---\n\n", "header")

            for block in reversed(self.blockchain.chain):  # 倒序显示，最新的在最前面
                is_valid_hash = block.get('hash', '')[:self.blockchain.get_difficulty()] == '0' * self.blockchain.get_difficulty()

                self.chain_text.insert(INSERT, f"区块 #{block.get('index')} ", "block_index")
                self.chain_text.insert(INSERT, f" (矿工: {block.get('miner')})\n")

                self.chain_text.insert(INSERT, f"  时间戳: {time.ctime(block.get('timestamp'))}\n")
                self.chain_text.insert(INSERT, f"  哈希: {block.get('hash')}\n")
                self.chain_text.insert(INSERT, f"  前一哈希: {block.get('previous_hash')}\n")
                self.chain_text.insert(INSERT, f"  证明(Nonce): {block.get('proof')}\n")

                hash_tag = "valid_hash" if is_valid_hash else "invalid_hash"
                self.chain_text.insert(INSERT, f"  难度检查: {is_valid_hash} (需要 {self.blockchain.get_difficulty()} 个 '0')\n", hash_tag)

                self.chain_text.insert(INSERT, "  交易列表:\n", "transaction_header")

                if not block.get('transactions'):
                    self.chain_text.insert(INSERT, "    (无交易)\n")
                for tx in block.get('transactions', []):
                    self.chain_text.insert(INSERT, f"    - {tx.get('sender')} -> {tx.get('recipient')} ({tx.get('amount', 0):.2f} T币)\n")
                self.chain_text.insert(INSERT, "-" * 60 + "\n\n")

            # 配置标签样式
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
            balances = self.blockchain.get_all_balances()

            if not balances:
                self.balance_text.insert(INSERT, "(暂无交易记录)")
            else:
                sorted_balances = sorted(balances.items(), key=lambda item: item[1], reverse=True)
                for user, balance in sorted_balances:
                    color = "#008000" if balance >= 0 else "#FF0000"

                    self.balance_text.insert(INSERT, f"{user.ljust(20)}: ", "user_name")
                    self.balance_text.insert(INSERT, f"{balance:.2f} T币\n", "balance_value")
                    self.balance_text.tag_config("user_name", font=('Consolas', 10, 'bold'))
                    self.balance_text.tag_config("balance_value", foreground=color, font=('Consolas', 10, 'bold'))

            self.balance_text.config(state=DISABLED)

        # 3. 待处理交易 (Pending Tab)
        elif current_tab_name == '待处理交易':
            self.pending_text.config(state=NORMAL)
            self.pending_text.delete(1.0, END)

            self.pending_text.insert(INSERT, "--- 待处理 (待打包) 交易 ---\n\n", "header")

            if not self.blockchain.pending_transactions:
                self.pending_text.insert(INSERT, "(暂无待处理交易)")
            else:
                for tx in self.blockchain.pending_transactions:
                    self.pending_text.insert(INSERT, f"时间: {time.ctime(tx.get('timestamp'))}\n", "time")
                    self.pending_text.insert(INSERT, f"- {tx.get('sender')} -> {tx.get('recipient')} ({tx.get('amount', 0):.2f} T币)\n", "tx_detail")
                    self.pending_text.insert(INSERT, f"  签名: {tx.get('signature','')[:20]}...\n\n", "signature")

            self.pending_text.tag_config("header", font=('Consolas', 10, 'bold'), foreground="#FFA500")
            self.pending_text.tag_config("time", foreground="#808080")
            self.pending_text.tag_config("tx_detail", font=('Consolas', 10, 'bold'))
            self.pending_text.config(state=DISABLED)

        # 更新状态栏余额和难度显示
        current_balance = self.blockchain.get_balance(self.miner_id)
        current_difficulty = self.blockchain.get_difficulty()
        self.difficulty_label.config(text=f"当前挖矿难度: {current_difficulty} ('0'开头)")

        if self.is_mining_continous:
            self.update_status_bar(f"⛏️ 持续挖矿中... | 钱包: {self.miner_id} | 余额: {current_balance:.2f} T币 | 待处理交易: {len(self.blockchain.pending_transactions)}")
        else:
            self.update_status_bar(f"就绪。| 钱包: {self.miner_id} | 余额: {current_balance:.2f} T币 | 待处理交易: {len(self.blockchain.pending_transactions)}")


#main
if __name__ == "__main__":
    if check_lockon()==False:
        full_launch()
    else:
        password_recover()







        
