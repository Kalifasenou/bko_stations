from django.contrib import admin
from .models import Station, Signalement


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    """Admin interface for Station model"""
    list_display = ['name', 'brand', 'latitude', 'longitude', 'status_color', 'created_at']
    list_filter = ['brand', 'created_at']
    search_fields = ['name', 'brand']
    readonly_fields = ['created_at', 'updated_at', 'status_color']
    ordering = ['name']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'brand')
        }),
        ('Localisation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'status_color'),
            'classes': ('collapse',)
        }),
    )


class SignalementInline(admin.TabularInline):
    """Inline admin for Signalement in Station"""
    model = Signalement
    extra = 0
    readonly_fields = ['timestamp', 'approval_count', 'ip']
    fields = ['fuel_type', 'status', 'timestamp', 'approval_count', 'ip']


@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    """Admin interface for Signalement model"""
    list_display = ['station', 'fuel_type', 'status', 'timestamp', 'approval_count', 'is_expired']
    list_filter = ['fuel_type', 'status', 'timestamp', 'station__brand']
    search_fields = ['station__name', 'station__brand']
    readonly_fields = ['timestamp', 'approval_count', 'ip', 'is_expired']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Signalement', {
            'fields': ('station', 'fuel_type', 'status')
        }),
        ('Métadonnées', {
            'fields': ('timestamp', 'approval_count', 'ip', 'is_expired'),
            'classes': ('collapse',)
        }),
    )
    
    def is_expired(self, obj):
        """Affiche si le signalement est expiré"""
        return obj.is_expired()
    
    is_expired.boolean = True
    is_expired.short_description = 'Expiré ?'


# Add inline to Station admin
StationAdmin.inlines = [SignalementInline]
