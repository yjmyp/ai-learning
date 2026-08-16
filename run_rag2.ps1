# RAG v2 one-click verify (build index -> retrieve test -> QA test)
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\29947\Documents\Codex\ai-learning'

Write-Host ''
Write-Host '========== 1/2 build index ==========' -ForegroundColor Cyan
python rag2\build_index.py

Write-Host ''
Write-Host '========== 2/2 retrieve + QA test ==========' -ForegroundColor Cyan
python rag2\test_rag2.py

Write-Host ''
Write-Host '========== 3/3 eval (hit-rate baseline) ==========' -ForegroundColor Cyan
python rag2\eval_rag2.py

Write-Host ''
Write-Host 'DONE!' -ForegroundColor Green
Read-Host 'Press Enter to close'
