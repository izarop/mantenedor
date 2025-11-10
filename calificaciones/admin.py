from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import CalificacionEncabezado, CalificacionFactores

@admin.register(CalificacionEncabezado)
class CalificacionEncabezadoAdmin(admin.ModelAdmin):
    list_display = ('anio','instrumento','mercado','origen','fecha_pago','pendiente','actualizado')
    search_fields = ('instrumento','descripcion')
    list_filter = ('anio','mercado','origen','pendiente')

@admin.register(CalificacionFactores)
class CalificacionFactoresAdmin(admin.ModelAdmin):
    list_display = ('encabezado',)
