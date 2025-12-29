from kardex.models import Prevision

existing = Prevision.objects.count()
if existing < 1500:
    Prevision.objects.bulk_create([
        Prevision(nombre=f"Prevision {i}")
        for i in range(existing + 1, 1501)
    ])
    print("✅ Registros agregados.")
else:
    print("⚠️ Ya hay 1500 o más registros.")
