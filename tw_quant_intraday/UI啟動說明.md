# UI 啟動說明

在 Windows 直接雙擊或從命令列執行：

```bat
start_ui.bat
```

啟動後會顯示：

- 策略輸出客戶端：`http://127.0.0.1:8765/strategy`
- Benchmark 測試界面：`http://127.0.0.1:8765/benchmark`

結束方式：

1. 回到 `start_ui.bat` 的命令視窗。
2. 按 Enter。
3. 腳本會自動停止本次啟動的 Python UI server 進程。

可選環境變數：

```bat
set TW_QUANT_OPEN_BROWSER=0
start_ui.bat
```

`TW_QUANT_OPEN_BROWSER=0` 表示只啟動 server，不自動開瀏覽器。

驗證模式：

```bat
set TW_QUANT_SMOKE=1
set TW_QUANT_OPEN_BROWSER=0
start_ui.bat
```

Smoke 模式會啟動 UI server，確認可用後等待約 2 秒，然後自動關閉 server。
