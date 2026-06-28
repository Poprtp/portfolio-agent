# AI Portfolio OS 2.0

Dashboard สำหรับดูแลพอร์ตหุ้น: allocation, risk, rebalance, watchlist ranking, price chart และ AI portfolio review.

## 1) เปิดโฟลเดอร์ใน VS Code

```powershell
cd D:\Portfolio-Agent-V2
```

หรือแตก ZIP แล้วเปิดโฟลเดอร์ด้วย VS Code

## 2) สร้าง virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

ถ้า PowerShell ไม่ให้ activate ให้รัน:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

## 3) ติดตั้ง package

```powershell
pip install -r requirements.txt
```

## 4) รัน Dashboard

```powershell
streamlit run app.py
```

หลังรัน จะเปิด browser ที่:

```text
http://localhost:8501
```

## 5) แก้พอร์ต

แก้ไฟล์นี้:

```text
data/holdings.csv
```

หรือแก้ในหน้า Dashboard ตรง `Edit Holdings`

ตัวอย่าง column:

```csv
ticker,name,shares,avg_cost,target_weight,asset_type
QQQI,NEOS Nasdaq-100 High Income ETF,132,52,35,Income ETF
TSM,Taiwan Semiconductor ADR,0,0,20,Growth Stock
```

## 6) เปิด AI Review

คัดลอก `.env.example` เป็น `.env`

```powershell
copy .env.example .env
```

ใส่ API key:

```text
OPENAI_API_KEY=your_api_key_here
```

แล้วรันใหม่:

```powershell
streamlit run app.py
```

## หมายเหตุ

- ราคาใช้ yfinance อาจโหลดช้าหรือบางครั้ง fail ได้
- TSMC ADR ใช้ ticker `TSM`
- QQQI ใช้ ticker `QQQI`
- ระบบนี้เป็น decision-support ไม่ใช่คำสั่งซื้อขายอัตโนมัติ
