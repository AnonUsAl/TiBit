import hashlib
import json
import time
import random
import tkinter as tk
from tkinter import messagebox, scrolledtext
import ctypes

# --- 简化常量 ---
MINING_DIFFICULTY = 1
MINING_REWARD = 5
GENESIS_PREV_HASH = "0" * 64
BLOCKCHAIN_FILENAME = "improved_tcoin_chain.json"


# --- 简单钱包模拟 ---
class Wallet:
    @staticmethod
    def generate_key_pair():
        private_key = hashlib.sha256(str(time.time() + random.random()).encode()).hexdigest()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()[:40]
        return public_key, private_key

    @staticmethod
    def sign_transaction(private_key, transaction_data):
        tx_string = json.dumps(transaction_data, sort_keys=True)
        return hashlib.sha256((tx_string + (private_key or "")).encode()).hexdigest()


# --- 区块链核心（移除 P2P、复杂美化与额外算法） ---
class Blockchain:
    def __init__(self):
        self.pending_transactions = []
        self.chain = []
        pub, priv = Wallet.generate_key_pair()
        self.wallets = {"My_Wallet": priv}
        self.addresses = {"My_Wallet": pub}

        if not self.load_chain(BLOCKCHAIN_FILENAME):
            # 简单创建创世块
            genesis = {
                'index': 1,
                'timestamp': time.time(),
                'transactions': [],
                'proof': 100,
                'previous_hash': GENESIS_PREV_HASH,
                'miner': "SYSTEM",
            }
            genesis['hash'] = self.hash_block(genesis)
            self.chain.append(genesis)

    @property
    def last_block(self):
        return self.chain[-1] if self.chain else None

    @staticmethod
    def hash_block(block):
        block_copy = {k: v for k, v in block.items() if k != 'hash'}
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def register_new_wallet(self, user_alias):
        public_key, private_key = Wallet.generate_key_pair()
        self.wallets[user_alias] = private_key
        self.addresses[user_alias] = public_key
        return public_key

    def new_transaction(self, sender, recipient, amount, sender_private_key=None):
        try:
            amount = float(amount)
        except ValueError:
            messagebox.showwarning("警告", "金额必须为数字。")
            return False

        if amount <= 0:
            messagebox.showwarning("警告", "金额必须为正数。")
            return False

        if sender != "SYSTEM":
            if self.get_balance(sender) < amount:
                messagebox.showerror("错误", "余额不足。")
                return False
            if not sender_private_key:
                messagebox.showerror("错误", "需要私钥签名。")
                return False

        tx_data = {'sender': sender, 'recipient': recipient, 'amount': amount, 'timestamp': time.time()}
        signature = Wallet.sign_transaction(sender_private_key or "", tx_data)
        transaction = {**tx_data, 'signature': signature}
        self.pending_transactions.append(transaction)
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

    def perform_proof_of_work(self, last_proof, transactions, difficulty):
        proof = 0
        while not self.is_valid_proof(last_proof, proof, transactions, difficulty):
            proof += 1
        return proof

    @staticmethod
    def is_valid_proof(last_proof, proof, transactions, difficulty):
        transactions_string = json.dumps(transactions, sort_keys=True).encode()
        guess = f'{last_proof}{proof}{transactions_string}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == '0' * difficulty

    def get_difficulty(self):
        return MINING_DIFFICULTY

    def get_balance(self, user):
        balance = 0.0
        for block in self.chain:
            for tx in block.get('transactions', []):
                if tx.get('sender') == user:
                    balance -= float(tx.get('amount', 0))
                if tx.get('recipient') == user:
                    balance += float(tx.get('amount', 0))
        return balance

    def get_all_balances(self):
        balances = {}
        for block in self.chain:
            for tx in block.get('transactions', []):
                s = tx.get('sender')
                r = tx.get('recipient')
                amt = float(tx.get('amount', 0))
                balances[s] = balances.get(s, 0.0) - amt
                balances[r] = balances.get(r, 0.0) + amt
        balances.pop("SYSTEM", None)
        return balances

    def is_chain_valid(self):
        if not self.chain:
            return True
        if self.chain[0].get('previous_hash') != GENESIS_PREV_HASH:
            messagebox.showerror("错误", "创世块 previous_hash 不匹配。")
            return False

        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            if curr.get('previous_hash') != self.hash_block(prev):
                messagebox.showerror("错误", f"区块 {i} 前一哈希不匹配。")
                return False
            if not self.is_valid_proof(prev.get('proof', 0), curr.get('proof'), curr.get('transactions', []), self.get_difficulty()):
                messagebox.showerror("错误", f"区块 {i} 工作量证明无效。")
                return False
            if curr.get('hash') != self.hash_block(curr):
                messagebox.showerror("错误", f"区块 {i} 哈希不匹配。")
                return False
        return True

    def save_chain(self, filename):
        try:
            data = {'chain': self.chain, 'pending_transactions': self.pending_transactions, 'wallets': self.wallets}
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            return False

    def load_chain(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.chain = data.get('chain', [])
                self.pending_transactions = data.get('pending_transactions', [])
                self.wallets = data.get('wallets', self.wallets)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False


# --- 简单 GUI（同时显示 区块链 / 余额 / 待处理，但保留切换逻辑） ---
class BlockchainApp:
    def __init__(self, root, blockchain: Blockchain):
        self.blockchain = blockchain
        self.root = root
        self.root.title("T币 挖矿v0.0.1 没有难度")
        self.root.geometry("800x600")
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        self.is_mining_continuous = False
        self.mining_interval_ms = 200

        self.miner_id = "My_Wallet"
        if self.miner_id not in self.blockchain.wallets:
            self.blockchain.register_new_wallet(self.miner_id)

        # 主布局：左控制，右显示（右侧同时显示三部分）
        left = tk.Frame(root, width=300)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        right = tk.Frame(root)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 控制区
        tk.Label(left, text=f"当前矿工 ({self.miner_id})").pack(anchor='w')
        self.miner_var = tk.StringVar(value=self.miner_id)
        tk.Entry(left, textvariable=self.miner_var).pack(fill=tk.X, pady=4)
        tk.Button(left, text="切换/创建钱包", command=self.set_miner).pack(fill=tk.X, pady=4)

        tk.Label(left, text="接收方").pack(anchor='w', pady=(10, 0))
        self.recipient_entry = tk.Entry(left)
        self.recipient_entry.pack(fill=tk.X)
        self.recipient_entry.insert(0, "Bob")

        tk.Label(left, text="金额").pack(anchor='w', pady=(6, 0))
        self.amount_entry = tk.Entry(left)
        self.amount_entry.pack(fill=tk.X)
        self.amount_entry.insert(0, "10.0")

        tk.Button(left, text="提交交易", command=self.create_transaction).pack(fill=tk.X, pady=6)
        tk.Button(left, text="单次挖矿", command=self.mine_block_single).pack(fill=tk.X, pady=6)

        self.start_btn = tk.Button(left, text="开始持续挖矿", command=self.start_continuous_mining)
        self.start_btn.pack(fill=tk.X, pady=4)
        self.stop_btn = tk.Button(left, text="停止持续挖矿", command=self.stop_continuous_mining, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=4)

        tk.Button(left, text="保存区块链", command=self.save_data).pack(fill=tk.X, pady=6)
        tk.Button(left, text="加载区块链", command=self.load_data).pack(fill=tk.X, pady=4)
        tk.Button(left, text="验证区块链", command=self.validate_chain).pack(fill=tk.X, pady=4)

        self.show_all_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left, text="显示全部视图", variable=self.show_all_var, onvalue=True, offvalue=False, command=lambda: self.show_view(self.selected_view)).pack(fill=tk.X, pady=4)

        # 按钮切换视图（保留原先逻辑）
        btn_frame_left = tk.Frame(left)
        btn_frame_left.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_frame_left, text="完整区块链", command=lambda: self.show_view('chain')).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(btn_frame_left, text="账户余额", command=lambda: self.show_view('balance')).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(btn_frame_left, text="待处理交易", command=lambda: self.show_view('pending')).pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.status_label = tk.Label(left, text="就绪。", anchor='w')
        self.status_label.pack(fill=tk.X, pady=(10, 0))

        # 右侧：同时显示 三个部分（完整区块链 / 账户余额 / 待处理交易）
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        # 完整区块链（上方，大）
        chain_frame = tk.Frame(right, bd=1, relief=tk.SUNKEN)
        chain_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        tk.Label(chain_frame, text="完整区块链").pack(anchor='w')
        chain_text = scrolledtext.ScrolledText(chain_frame, wrap=tk.WORD, state=tk.DISABLED, font=('Consolas', 10))
        chain_text.pack(fill=tk.BOTH, expand=True)
        self.view_chain = chain_text
        self.chain_frame = chain_frame

        # 账户余额（中）
        bal_frame = tk.Frame(right, bd=1, relief=tk.SUNKEN)
        bal_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        tk.Label(bal_frame, text="账户余额").pack(anchor='w')
        bal_text = scrolledtext.ScrolledText(bal_frame, wrap=tk.WORD, state=tk.DISABLED, height=6, font=('Consolas', 10))
        bal_text.pack(fill=tk.BOTH, expand=True)
        self.view_balance = bal_text
        self.bal_frame = bal_frame

        # 待处理交易（下）
        pend_frame = tk.Frame(right, bd=1, relief=tk.SUNKEN)
        pend_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        tk.Label(pend_frame, text="待处理交易").pack(anchor='w')
        pend_text = scrolledtext.ScrolledText(pend_frame, wrap=tk.WORD, state=tk.DISABLED, height=6, font=('Consolas', 10))
        pend_text.pack(fill=tk.BOTH, expand=True)
        self.view_pending = pend_text
        self.pend_frame = pend_frame

        # 记录当前选中视图（供切换逻辑使用）
        self.selected_view = 'chain'

        # 初始化显示
        self.update_display()
        # 应用初始视图/布局（show_all True -> all visible + highlight selected）
        self.show_view(self.selected_view)

    def set_miner(self):
        new = self.miner_var.get().strip()
        if not new:
            messagebox.showerror("错误", "钱包名不能为空。")
            self.miner_var.set(self.miner_id)
            return
        if new not in self.blockchain.wallets:
            addr = self.blockchain.register_new_wallet(new)
            messagebox.showinfo("提示", f"已创建钱包 {new}\n地址: {addr}")
        self.miner_id = new
        self.update_display()

    def create_transaction(self):
        sender = self.miner_id
        recipient = self.recipient_entry.get().strip()
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("错误", "金额必须为数字。")
            return
        if not sender or not recipient:
            messagebox.showerror("错误", "发送方或接收方不能为空。")
            return
        priv = self.blockchain.wallets.get(sender)
        if not priv:
            messagebox.showerror("错误", "找不到私钥。")
            return
        if self.blockchain.new_transaction(sender, recipient, amount, priv):
            messagebox.showinfo("提示", "交易已添加。")
            self.update_display()

    def mine_block_logic(self):
        last = self.blockchain.last_block
        last_proof = last.get('proof', 0) if last else 0
        prev_hash = last.get('hash', GENESIS_PREV_HASH) if last else GENESIS_PREV_HASH
        txs = list(self.blockchain.pending_transactions)
        reward = {'sender': "SYSTEM", 'recipient': self.miner_id, 'amount': MINING_REWARD, 'timestamp': time.time()}
        reward['signature'] = Wallet.sign_transaction("SYSTEM", reward)
        txs.insert(0, reward)
        difficulty = self.blockchain.get_difficulty()
        start = time.time()
        proof = self.blockchain.perform_proof_of_work(last_proof, txs, difficulty)
        elapsed = time.time() - start
        self.blockchain.pending_transactions = []
        block = self.blockchain.mine_block(proof, prev_hash, txs, self.miner_id)
        return block, elapsed

    def mine_block_single(self):
        self.status_label.config(text="挖矿中...")
        self.root.update_idletasks()
        try:
            block, elapsed = self.mine_block_logic()
            messagebox.showinfo("挖矿成功", f"区块 #{block['index']} 已挖出，耗时 {elapsed:.2f}s，奖励 {MINING_REWARD} T币。")
            self.update_display()
        except Exception as e:
            messagebox.showerror("错误", f"挖矿失败: {e}")
        finally:
            self.status_label.config(text="就绪。")

    def start_continuous_mining(self):
        if self.is_mining_continuous:
            return
        self.is_mining_continuous = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._continuous_loop()

    def stop_continuous_mining(self):
        self.is_mining_continuous = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        messagebox.showinfo("提示", "已停止持续挖矿。")

    def _continuous_loop(self):
        if not self.is_mining_continuous:
            return
        try:
            block, elapsed = self.mine_block_logic()
            self.status_label.config(text=f"持续挖矿：找到了区块 #{block['index']}，用时 {elapsed:.2f}s")
            self.update_display()
        except Exception as e:
            messagebox.showerror("错误", f"持续挖矿出错: {e}")
            self.stop_continuous_mining()
            return
        self.root.after(self.mining_interval_ms, self._continuous_loop)

    def save_data(self):
        if self.blockchain.save_chain(BLOCKCHAIN_FILENAME):
            messagebox.showinfo("提示", f"已保存到 {BLOCKCHAIN_FILENAME}")
            self.update_display()
        else:
            messagebox.showerror("错误", "保存失败。")

    def load_data(self):
        if messagebox.askyesno("确认", "加载将覆盖当前未保存的数据，确定？"):
            if self.blockchain.load_chain(BLOCKCHAIN_FILENAME):
                messagebox.showinfo("提示", "加载成功。")
                self.update_display()
            else:
                messagebox.showerror("错误", "加载失败或文件不存在。")

    def validate_chain(self):
        ok = self.blockchain.is_chain_valid()
        if ok:
            messagebox.showinfo("验证", "区块链验证通过。")
        else:
            messagebox.showerror("验证", "区块链验证失败。")

    # 布局：全部视图
    def layout_views_all(self):
        # 将三个 panel 放回原始三行布局
        try:
            self.chain_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
            self.bal_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
            self.pend_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        except Exception:
            pass

    # 布局：单视图
    def layout_single_view(self, name):
        # 隐藏所有然后仅显示选中
        try:
            self.chain_frame.grid_remove()
            self.bal_frame.grid_remove()
            self.pend_frame.grid_remove()
        except Exception:
            pass

        if name == 'chain':
            self.chain_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        elif name == 'balance':
            self.bal_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        elif name == 'pending':
            self.pend_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def show_view(self, name):
        # 记录选择
        self.selected_view = name
        if self.show_all_var.get():
            # 显示全部，但高亮选中面板
            self.layout_views_all()
            # 重置样式
            for f in (self.chain_frame, self.bal_frame, self.pend_frame):
                try:
                    f.config(relief=tk.SUNKEN, bd=1)
                except Exception:
                    pass
            # 高亮选中
            target = {'chain': self.chain_frame, 'balance': self.bal_frame, 'pending': self.pend_frame}.get(name)
            if target:
                try:
                    target.config(relief=tk.RAISED, bd=3)
                except Exception:
                    pass
        else:
            # 使用原先的隐藏/显示逻辑（仅显示选中）
            self.layout_single_view(name)

        # 保证内容刷新
        self.update_display()

    def update_display(self):
        # 完整区块链（上）
        chain_text: scrolledtext.ScrolledText = self.view_chain
        chain_text.config(state=tk.NORMAL)
        chain_text.delete(1.0, tk.END)
        chain_text.insert(tk.INSERT, f"--- T币 区块链 (长度: {len(self.blockchain.chain)}) ---\n\n")
        for block in reversed(self.blockchain.chain):
            chain_text.insert(tk.INSERT, f"区块 #{block.get('index')} (矿工: {block.get('miner')})\n")
            chain_text.insert(tk.INSERT, f" 时间: {time.ctime(block.get('timestamp'))}\n")
            chain_text.insert(tk.INSERT, f" 哈希: {block.get('hash')}\n")
            chain_text.insert(tk.INSERT, f" 前一哈希: {block.get('previous_hash')}\n")
            chain_text.insert(tk.INSERT, f" 交易数: {len(block.get('transactions', []))}\n")
            for tx in block.get('transactions', []):
                chain_text.insert(tk.INSERT, f"   - {tx.get('sender')} -> {tx.get('recipient')} ({float(tx.get('amount', 0)):.2f})\n")
            chain_text.insert(tk.INSERT, "-" * 50 + "\n")
        chain_text.config(state=tk.DISABLED)

        # 余额视图（中）
        bal_text: scrolledtext.ScrolledText = self.view_balance
        bal_text.config(state=tk.NORMAL)
        bal_text.delete(1.0, tk.END)
        bal_text.insert(tk.INSERT, "--- 账户余额 ---\n\n")
        balances = self.blockchain.get_all_balances()
        if not balances:
            bal_text.insert(tk.INSERT, "(暂无交易记录)\n")
        else:
            for user, bal in sorted(balances.items(), key=lambda x: x[1], reverse=True):
                bal_text.insert(tk.INSERT, f"{user.ljust(20)}: {bal:.2f} T币\n")
        bal_text.config(state=tk.DISABLED)

        # 待处理视图（下）
        pend_text: scrolledtext.ScrolledText = self.view_pending
        pend_text.config(state=tk.NORMAL)
        pend_text.delete(1.0, tk.END)
        pend_text.insert(tk.INSERT, "--- 待处理交易 ---\n\n")
        if not self.blockchain.pending_transactions:
            pend_text.insert(tk.INSERT, "(暂无待处理交易)\n")
        else:
            for tx in self.blockchain.pending_transactions:
                pend_text.insert(tk.INSERT, f"时间: {time.ctime(tx.get('timestamp'))}\n")
                pend_text.insert(tk.INSERT, f"  {tx.get('sender')} -> {tx.get('recipient')} ({float(tx.get('amount',0)):.2f})\n\n")
        pend_text.config(state=tk.DISABLED)

        # 更新状态栏信息
        bal = self.blockchain.get_balance(self.miner_id)
        diff = self.blockchain.get_difficulty()
        self.status_label.config(text=f"钱包: {self.miner_id} | 余额: {bal:.2f} | 难度: {diff} | 待处理: {len(self.blockchain.pending_transactions)}")


if __name__ == "__main__":
    try:
        root = tk.Tk()
        bc = Blockchain()
        app = BlockchainApp(root, bc)
        root.mainloop()
    except Exception as e:
        try:
            messagebox.showerror("错误", f"程序异常: {e}")
        except Exception:
            print("程序异常:", e)
        try:
            bc.save_chain(BLOCKCHAIN_FILENAME)
        except Exception:
            pass
