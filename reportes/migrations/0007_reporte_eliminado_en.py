# Generated for change "eliminar reporte" (soft delete). Single additive
# `AddField`, nullable with `default=None` — no existing row's meaning
# changes (every existing `Reporte` stays live: `eliminado_en IS NULL`).
# Rollback: `manage.py migrate reportes 0006`.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0006_adjunto'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporte',
            name='eliminado_en',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
