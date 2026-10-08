"""
Bước 1: Kiểm tra Russell 1000 Universe
=======================================
Mục đích: Đếm số lượng mã cổ phiếu (tickers) trong từng năm 2000-2026
          và vẽ biểu đồ cột để trực quan hóa.

Cách hoạt động:
  - Đọc từng file russell1000_{year}.json trong thư mục by_year/
  - Mỗi file JSON chứa 1 danh sách (list) các ticker strings, ví dụ: ["AAPL", "MSFT", ...]
  - Đếm len() của danh sách đó = số mã cổ phiếu trong năm
  - Vẽ biểu đồ cột (bar chart) bằng matplotlib
"""
import os, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # Dùng backend không cần GUI (chạy trên server/terminal)

# ===== BƯỚC 1: Thiết lập đường dẫn =====
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERSE_DIR = os.path.join(BASE, "data", "raw", "universe", "by_year")
OUTPUT_DIR   = os.path.join(BASE, "outputs", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===== BƯỚC 2: Đọc từng file JSON và đếm số mã =====
years = []
counts = []

for year in range(2000, 2027):
    json_path = os.path.join(UNIVERSE_DIR, f"russell1000_{year}.json")
    
    if not os.path.exists(json_path):
        print(f"⚠️ File {json_path} không tồn tại, bỏ qua năm {year}")
        continue
    
    with open(json_path, "r") as f:
        tickers = json.load(f)  # Đọc danh sách tickers từ JSON
    
    years.append(year)
    counts.append(len(tickers))
    print(f"  Năm {year}: {len(tickers)} mã cổ phiếu")

# ===== BƯỚC 3: Tính toán thống kê cơ bản =====
avg_count = sum(counts) / len(counts)
min_count = min(counts)
max_count = max(counts)
min_year  = years[counts.index(min_count)]
max_year  = years[counts.index(max_count)]

print(f"\n--- THỐNG KÊ TỔNG HỢP ---")
print(f"  Số năm          : {len(years)} năm (2000-2026)")
print(f"  Trung bình/năm  : {avg_count:.0f} mã")
print(f"  Ít nhất         : {min_count} mã (năm {min_year})")
print(f"  Nhiều nhất      : {max_count} mã (năm {max_year})")

# Tổng số mã unique qua tất cả các năm
all_tickers = set()
for year in range(2000, 2027):
    json_path = os.path.join(UNIVERSE_DIR, f"russell1000_{year}.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            all_tickers.update(json.load(f))
print(f"  Tổng unique     : {len(all_tickers)} mã duy nhất (suốt 27 năm)")

# ===== BƯỚC 4: Vẽ biểu đồ cột =====
fig, ax = plt.subplots(figsize=(16, 7))

# Tô màu: xanh nếu >= 990, cam nếu < 990
colors = ["#2e7d32" if c >= 990 else "#e65100" for c in counts]

bars = ax.bar(years, counts, color=colors, edgecolor="white", width=0.7)

# Thêm số liệu lên đầu mỗi cột
for bar, count in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
            str(count), ha="center", va="bottom", fontsize=8, fontweight="bold")

# Đường tham chiếu 1000
ax.axhline(y=1000, color="red", linestyle="--", linewidth=1.2, label="Mức chuẩn 1,000 mã")

# Trang trí biểu đồ
ax.set_xlabel("Năm", fontsize=12, fontweight="bold")
ax.set_ylabel("Số lượng mã cổ phiếu", fontsize=12, fontweight="bold")
ax.set_title("Russell 1000 Universe: Số lượng mã cổ phiếu theo từng năm (2000–2026)",
             fontsize=14, fontweight="bold", pad=15)
ax.set_xticks(years)
ax.set_xticklabels(years, rotation=45, ha="right")
ax.set_ylim(950, max_count + 20)
ax.legend(loc="lower right", fontsize=10)
ax.grid(axis="y", alpha=0.3)

# Chú thích màu
ax.text(0.02, 0.95, "[Xanh] >= 990 ma  |  [Cam] < 990 ma",
        transform=ax.transAxes, fontsize=9, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

plt.tight_layout()
fig_path = os.path.join(OUTPUT_DIR, "step1_universe_count_by_year.png")
plt.savefig(fig_path, dpi=150, bbox_inches="tight")
print(f"\n✅ Biểu đồ đã lưu tại: {fig_path}")
