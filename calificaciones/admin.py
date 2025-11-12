# # Register your models here.
# from django.contrib import admin
# from .models import CalificacionEncabezado, CalificacionFactores

# @admin.register(CalificacionEncabezado)
# class CalificacionEncabezadoAdmin(admin.ModelAdmin):
#     list_display = ('anio','instrumento','mercado','origen','fecha_pago','pendiente','actualizado')
#     search_fields = ('instrumento','descripcion')
#     list_filter = ('anio','mercado','origen','pendiente')

# @admin.register(CalificacionFactores)
# class CalificacionFactoresAdmin(admin.ModelAdmin):
#     list_display = ('encabezado',)
# admin.py
from django.contrib import admin
from .models import CalificacionEncabezado, CalificacionFactores, Perfil

class CalificacionFactoresInline(admin.StackedInline):
    model = CalificacionFactores
    can_delete = False
    extra = 0

@admin.register(CalificacionEncabezado)
class CalificacionEncabezadoAdmin(admin.ModelAdmin):
    list_display = ('id','anio','instrumento','mercado','origen','fecha_pago','pendiente','actualizado')
    search_fields = ('instrumento','descripcion')
    list_filter = ('anio','mercado','origen','pendiente')
    inlines = [CalificacionFactoresInline]

@admin.register(CalificacionFactores)
class CalificacionFactoresAdmin(admin.ModelAdmin):
    list_display = ('encabezado',)

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user','rol','institucion')
    list_filter = ('rol',)
    search_fields = ('user__username', 'institucion')
