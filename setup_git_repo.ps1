# ============================================================
# MAEA-HCDS GitHub 仓库初始化脚本
# 论文: 情绪扰动、激励阻断与协同鲁棒：多智能体供应链牛鞭效应缓解研究
# ============================================================
# 用途: 在本地将项目目录初始化为 Git 仓库, 提交首版后可推送至 GitHub
# 使用:
#   1. 以管理员/普通用户身份打开 PowerShell
#   2. cd 到本仓库根目录
#   3. powershell -ExecutionPolicy Bypass -File setup_git_repo.ps1
# ============================================================

# 严格模式
$ErrorActionPreference = "Stop"

# 切换到脚本所在目录
Set-Location -Path $PSScriptRoot
Write-Host "================================" -ForegroundColor Cyan
Write-Host "MAEA-HCDS GitHub 仓库初始化" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "工作目录: $(Get-Location)" -ForegroundColor Gray
Write-Host ""

# 1. 检查 Git 是否安装
Write-Host "[1/7] 检查 Git 安装..." -ForegroundColor Yellow
try {
    $gitVersion = git --version
    Write-Host "  [OK] $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Git 未安装, 请先安装: https://git-scm.com/downloads" -ForegroundColor Red
    exit 1
}

# 2. 检查关键文件存在性
Write-Host "[2/7] 检查关键文件..." -ForegroundColor Yellow
$keyFiles = @(
    "README.md", "LICENSE", "CITATION.cff", "requirements.txt",
    "config.yaml", "config.py", ".gitignore",
    "supply_chain_env.py", "idmr_agent.py", "emotion_module.py",
    "continual_idmr.py", "ewc.py", "prioritized_replay.py",
    "batch_runner.py", "generate_paper_figures_719.py",
    "docs/REPO_STRUCTURE.md"
)
$missingFiles = @()
foreach ($f in $keyFiles) {
    if (Test-Path $f) {
        Write-Host "  [OK] $f" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $f" -ForegroundColor Red
        $missingFiles += $f
    }
}
if ($missingFiles.Count -gt 0) {
    Write-Host "  [WARN] 缺失 $($missingFiles.Count) 个文件, 但可继续" -ForegroundColor Yellow
}
Write-Host ""

# 3. 检查 719版论文配图存在性
Write-Host "[3/7] 检查 719版论文配图..." -ForegroundColor Yellow
$figFiles = @(
    "svg_figures_paper_719/Fig1_System_Mechanism.pdf",
    "svg_figures_paper_719/Fig1_System_Mechanism.svg",
    "svg_figures_paper_719/Fig1_System_Mechanism.png",
    "svg_figures_paper_719/Fig2_Decision_Flow.pdf",
    "svg_figures_paper_719/Fig2_Decision_Flow.svg",
    "svg_figures_paper_719/Fig2_Decision_Flow.png",
    "svg_figures_paper_719/Fig8_Emotion_Contagion.pdf",
    "svg_figures_paper_719/Fig8_Emotion_Contagion.svg",
    "svg_figures_paper_719/Fig8_Emotion_Contagion.png"
)
foreach ($f in $figFiles) {
    if (Test-Path $f) {
        $size = (Get-Item $f).Length
        Write-Host ("  [OK] {0} ({1:N0} bytes)" -f $f, $size) -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $f" -ForegroundColor Red
    }
}
Write-Host ""

# 4. 检查 719版论文docx存在性
Write-Host "[4/7] 检查 719版论文..." -ForegroundColor Yellow
$paperFile = "情绪扰动、激励阻断与协同鲁棒：多智能体供应链牛鞭效应缓解研究_719修改后.docx"
if (Test-Path $paperFile) {
    $size = (Get-Item $paperFile).Length
    Write-Host ("  [OK] {0} ({1:N0} bytes)" -f $paperFile, $size) -ForegroundColor Green
} else {
    Write-Host "  [MISSING] $paperFile" -ForegroundColor Red
}
Write-Host ""

# 5. 初始化 Git 仓库
Write-Host "[5/7] 初始化 Git 仓库..." -ForegroundColor Yellow
if (Test-Path ".git") {
    Write-Host "  [INFO] .git 目录已存在, 跳过初始化" -ForegroundColor Yellow
} else {
    git init
    Write-Host "  [OK] Git 仓库已初始化" -ForegroundColor Green
}

# 配置默认分支名为 main
try {
    git symbolic-ref HEAD refs/heads/main 2>$null
    Write-Host "  [OK] 默认分支设置为 main" -ForegroundColor Green
} catch {
    Write-Host "  [INFO] 默认分支设置跳过" -ForegroundColor Gray
}
Write-Host ""

# 6. 检查将入库的文件数量
Write-Host "[6/7] 统计将入库的文件..." -ForegroundColor Yellow
$statusOutput = git status --porcelain 2>$null
$trackedCount = ($statusOutput | Measure-Object).Count
Write-Host "  [INFO] 待提交文件数: $trackedCount" -ForegroundColor Green
Write-Host ""

# 7. 提示下一步操作
Write-Host "[7/7] 下一步操作指引..." -ForegroundColor Yellow
Write-Host "  1. 手动检查 git status:" -ForegroundColor White
Write-Host "       git status" -ForegroundColor Gray
Write-Host "  2. 添加所有文件到暂存区:" -ForegroundColor White
Write-Host "       git add ." -ForegroundColor Gray
Write-Host "  3. 首次提交:" -ForegroundColor White
Write-Host '       git commit -m "v719: MAEA-HCDS 多智能体情绪感知人智协同决策系统 (719修改后版)"' -ForegroundColor Gray
Write-Host "  4. 在 GitHub 创建空仓库后绑定远程:" -ForegroundColor White
Write-Host "       git remote add origin https://github.com/<your-username>/MAEA-HCDS.git" -ForegroundColor Gray
Write-Host "  5. 推送到 GitHub:" -ForegroundColor White
Write-Host "       git branch -M main" -ForegroundColor Gray
Write-Host "       git push -u origin main" -ForegroundColor Gray
Write-Host ""

Write-Host "================================" -ForegroundColor Cyan
Write-Host "初始化完成!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "提示: 首次运行 git commit 前请配置用户信息:" -ForegroundColor Yellow
Write-Host '  git config user.name "Yang Lixiang"' -ForegroundColor Gray
Write-Host '  git config user.email "yanglixiang@stdu.ysu.edu.cn"' -ForegroundColor Gray
Write-Host ""
