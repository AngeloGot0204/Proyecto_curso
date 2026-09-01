"""Regenera la plantilla `.xlsx` base del formato JME.PC-0001.F1.

La plantilla es un binario: sin esta orden nadie puede reproducirla ni
auditar por qué quedó como quedó. Autorarla desde código la vuelve
revisable en el diff y regenerable ante cualquier ajuste de formato.
"""

from django.core.management.base import BaseCommand

from tipos_reporte.plantilla_base import construir


class Command(BaseCommand):
    help = "Escribe la plantilla base del formato JME.PC-0001.F1 en <destino>."

    def add_arguments(self, parser):
        parser.add_argument("destino", help="Ruta del .xlsx a escribir.")

    def handle(self, *args, **opciones):
        destino = opciones["destino"]
        construir().save(destino)
        self.stdout.write(self.style.SUCCESS(f"Plantilla escrita en {destino}"))
