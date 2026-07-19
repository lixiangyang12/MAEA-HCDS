﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿
# daily_action_list.ps1
# 每日行动清单 - 拉取今日待办任务和日历，生成行动清单发送给自己
# 由 Windows 任务计划程序每天 08:00 自动执行

# ===== 编码设置 =====
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 > $null 2>&1

# ===== 环境设置 =====
$env:Path = "C:\Users\ylx88\AppData\Roaming\npm;" + $env:Path

# ===== 配置 =====
$baseToken = "SZWobOee1arU9ksJFrgc6sH6n5c"
$tableId = "tbl7da0XNY8Jy0SE"
$myOpenId = "ou_0e4eef81d79d7b9bf5d20a98284e9892"

# 字段索引（固定顺序，避免编码问题）
# 0: 任务名称, 1: 备注, 2: 分类, 3: 状态, 4: 截止日期, 5: 优先级
$IDX_NAME = 0
$IDX_NOTE = 1
$IDX_CATEGORY = 2
$IDX_STATUS = 3
$IDX_DEADLINE = 4
$IDX_PRIORITY = 5

# ===== 获取今日日期 =====
$today = Get-Date
$todayDate = $today.Date
$todayStr = $today.ToString("yyyy-MM-dd")
$todayStart = "${todayStr}T00:00:00+08:00"
$todayEnd = "${todayStr}T23:59:59+08:00"
$weekdays = @("周日","周一","周二","周三","周四","周五","周六")
$dateDisplay = $today.ToString("yyyy年MM月dd日") + " " + $weekdays[$today.DayOfWeek.value__]

# ===== 1. 拉取多维表格所有记录 =====
$allRows = @()
try {
    $recordsRaw = lark-cli base +record-list --base-token $baseToken --table-id $tableId --limit 200 --format json --as user | Out-String
    $recordsObj = $recordsRaw | ConvertFrom-Json
    $allRows = @($recordsObj.data.data)
    Write-Output "[DEBUG] Total records: $($allRows.Count)"
} catch {
    Write-Output "[ERROR] Failed to fetch records: $($_.Exception.Message)"
    $allRows = @()
}

# 筛选今日截止的任务
$todayTasks = @()
foreach ($row in $allRows) {
    $deadlineStr = $row[$IDX_DEADLINE]
    if ($deadlineStr -and $deadlineStr -ne $null) {
        try {
            $deadline = [DateTime]::Parse($deadlineStr)
            if ($deadline.Date -eq $todayDate) {
                $todayTasks += ,$row
            }
        } catch {}
    }
}
Write-Output "[DEBUG] Today tasks: $($todayTasks.Count)"

# ===== 2. 拉取今日日历 =====
$events = @()
try {
    $agendaRaw = lark-cli calendar +agenda --start $todayStart --end $todayEnd --format json --as user | Out-String
    $agendaObj = $agendaRaw | ConvertFrom-Json
    $events = @($agendaObj.data)
    Write-Output "[DEBUG] Calendar events: $($events.Count)"
} catch {
    Write-Output "[ERROR] Failed to fetch calendar: $($_.Exception.Message)"
    $events = @()
}

# ===== 3. 生成行动清单 =====
$msg = "## 每日行动清单`n`n"
$msg += "**$dateDisplay**`n`n"
$msg += "---`n`n"

# --- 日程 ---
$msg += "### 日程安排`n`n"
if ($events -and $events.Count -gt 0) {
    foreach ($event in $events) {
        $summary = if ($event.summary) { $event.summary } elseif ($event.title) { $event.title } else { "（无标题）" }
        $startTime = if ($event.start_time) { $event.start_time } elseif ($event.start) { $event.start } else { "" }
        $endTime = if ($event.end_time) { $event.end_time } elseif ($event.end) { $event.end } else { "" }
        $location = if ($event.location) { " | $event.location" } else { "" }
        if ($startTime -and $endTime) {
            $msg += "- ${startTime}~${endTime} $summary$location`n"
        } else {
            $msg += "- $summary$location`n"
        }
    }
} else {
    $msg += "今日无日程安排`n"
}
$msg += "`n"

# --- 任务 ---
if ($todayTasks.Count -gt 0) {
    # 按分类分组
    $enterpriseTasks = @()
    $researchTasks = @()
    foreach ($t in $todayTasks) {
        $cat = $t[$IDX_CATEGORY]
        if ($cat -is [System.Array]) {
            $catStr = $cat[0]
        } else {
            $catStr = "$cat"
        }
        # 匹配分类（处理可能的编码差异，用特征匹配）
        if ($catStr -match ".*营.*" -or $catStr -match "enterprise") {
            $enterpriseTasks += ,$t
        } elseif ($catStr -match ".*研.*" -or $catStr -match "research") {
            $researchTasks += ,$t
        } else {
            $enterpriseTasks += ,$t
        }
    }

    # 企业日常运营
    $msg += "### 企业日常运营`n`n"
    if ($enterpriseTasks.Count -gt 0) {
        foreach ($t in $enterpriseTasks) {
            $name = $t[$IDX_NAME]
            $statusArr = $t[$IDX_STATUS]
            $status = if ($statusArr -is [System.Array]) { $statusArr[0] } else { "$statusArr" }
            $priArr = $t[$IDX_PRIORITY]
            $priority = if ($priArr -is [System.Array]) { $priArr[0] } else { "$priArr" }
            $deadline = $t[$IDX_DEADLINE]
            $note = $t[$IDX_NOTE]
            $deadlineShort = ""
            try { $deadlineShort = ([DateTime]::Parse($deadline)).ToString("HH:mm") } catch { $deadlineShort = $deadline }
            $msg += "- **[$priority]** $name`n  截止: $deadlineShort | 状态: $status`n"
            if ($note -and $note -ne $null -and "$note".Trim() -ne "") {
                $msg += "  备注: $note`n"
            }
        }
    } else {
        $msg += "今日无企业运营任务`n"
    }
    $msg += "`n"

    # 博士科研任务
    $msg += "### 博士科研任务`n`n"
    if ($researchTasks.Count -gt 0) {
        foreach ($t in $researchTasks) {
            $name = $t[$IDX_NAME]
            $statusArr = $t[$IDX_STATUS]
            $status = if ($statusArr -is [System.Array]) { $statusArr[0] } else { "$statusArr" }
            $priArr = $t[$IDX_PRIORITY]
            $priority = if ($priArr -is [System.Array]) { $priArr[0] } else { "$priArr" }
            $deadline = $t[$IDX_DEADLINE]
            $note = $t[$IDX_NOTE]
            $deadlineShort = ""
            try { $deadlineShort = ([DateTime]::Parse($deadline)).ToString("HH:mm") } catch { $deadlineShort = $deadline }
            $msg += "- **[$priority]** $name`n  截止: $deadlineShort | 状态: $status`n"
            if ($note -and $note -ne $null -and "$note".Trim() -ne "") {
                $msg += "  备注: $note`n"
            }
        }
    } else {
        $msg += "今日无科研任务`n"
    }
} else {
    $msg += "### 今日任务`n`n今日无待办任务`n"
}
$msg += "`n---`n`n*本清单由自动化脚本每日 08:00 自动生成*"

# ===== 4. 发送消息 =====
Write-Output "[DEBUG] Message length: $($msg.Length)"
try {
    $result = lark-cli im +messages-send --user-id $myOpenId --markdown $msg --as user | Out-String
    Write-Output "[DEBUG] Send result: $result"
    $resultObj = $result | ConvertFrom-Json
    if ($resultObj.ok) {
        Write-Output "SUCCESS: 每日行动清单已发送"
    } else {
        Write-Output "FAILED: $($resultObj.error.message)"
    }
} catch {
    Write-Output "ERROR: $($_.Exception.Message)"
}
