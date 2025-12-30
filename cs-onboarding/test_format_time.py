import sys
sys.path.insert(0, 'backend')

from project.domain.dashboard.utils import format_relative_time
from datetime import datetime, timezone

# Simular o timestamp que vem do banco (com timezone UTC)
# Comentário feito às 09:18 BRT = 12:18 UTC
timestamp_banco = datetime(2025, 12, 30, 12, 18, 10, 474789, tzinfo=timezone.utc)

print("=" * 80)
print("TESTE DA FUNÇÃO format_relative_time")
print("=" * 80)
print(f"\nTimestamp do banco: {timestamp_banco}")
print(f"Horário atual UTC: {datetime.now(timezone.utc)}")

text, days, status = format_relative_time(timestamp_banco)

print(f"\nResultado:")
print(f"  Texto: {text}")
print(f"  Dias: {days}")
print(f"  Status: {status}")
print("\n" + "=" * 80)
