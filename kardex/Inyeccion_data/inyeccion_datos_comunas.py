from kardex.models import Comuna

existing = Comuna.objects.count()
if existing < 1500:
    Comuna.objects.bulk_create([
        Comuna(nombre=f"Comuna {i}")
        for i in range(existing + 1, 1501)
    ])
    print("✅ Registros agregados.")
else:
    print("⚠️ Ya hay 1500 o más registros.")
