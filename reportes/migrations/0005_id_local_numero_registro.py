# Generated for change `sincronizacion-numero-registro` (design D1, D2, D8).
#
# Migration ordering is deliberate and MUST NOT be reordered:
#   1. RunSQL creates the Postgres sequence FIRST — the column DEFAULT below
#      references it by name, so the sequence must already exist.
#   2. AddField `id_local` — UUIDField, DB-side `gen_random_uuid()` default
#      (D2). Volatile function, so `ADD COLUMN` backfills a distinct value
#      per existing row.
#   3. AddField `numero_registro` — BigIntegerField, DB-side `nextval(...)`
#      default (D1). Also volatile, so existing rows get distinct sequential
#      numbers too.
#
# Reversing this migration drops both columns before dropping the sequence
# (Django reverses `operations` in list order), which is the clean order:
# nothing still references the sequence by the time it is dropped.

from django.db import migrations, models
from django.db.models import Func, Value


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0004_participacion_cambiodevalor'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SEQUENCE IF NOT EXISTS reportes_numero_registro_seq",
            reverse_sql="DROP SEQUENCE IF EXISTS reportes_numero_registro_seq",
        ),
        migrations.AddField(
            model_name='reporte',
            name='id_local',
            field=models.UUIDField(
                unique=True,
                editable=False,
                db_default=Func(function="gen_random_uuid"),
            ),
        ),
        migrations.AddField(
            model_name='reporte',
            name='numero_registro',
            field=models.BigIntegerField(
                unique=True,
                editable=False,
                db_default=Func(
                    Value("reportes_numero_registro_seq"), function="nextval"
                ),
            ),
        ),
    ]
