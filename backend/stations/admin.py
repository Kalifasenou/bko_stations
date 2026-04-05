from django.contrib import admin
from .models import Station, Signalement, ZoneElectrique, ElectriciteSignalement


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    """Admin interface for Station model"""
    list_display = ['name', 'brand', 'latitude', 'longitude', 'is_active', 'has_recent_signalement', 'status_color', 'created_at']
    list_filter = ['brand', 'is_active', 'created_at']
    search_fields = ['name', 'brand', 'address', 'manager_name']
    readonly_fields = ['created_at', 'updated_at', 'status_color', 'has_recent_signalement']
    ordering = ['name']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'brand', 'is_active')
        }),
        ('Localisation', {
            'fields': ('latitude', 'longitude', 'address')
        }),
        ('Gestion', {
            'fields': ('manager_name', 'phone')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'status_color', 'has_recent_signalement'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
    mark_as_active.short_description = "Marquer les stations sélectionnées comme actives"
    
    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
    mark_as_inactive.short_description = "Marquer les stations sélectionnées comme inactives"


class SignalementInline(admin.TabularInline):
    """Inline admin for Signalement in Station"""
    model = Signalement
    extra = 0
    readonly_fields = ['timestamp', 'approval_count', 'ip', 'is_expired']
    fields = ['fuel_type', 'status', 'timestamp', 'approval_count', 'ip', 'is_expired']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ZoneElectrique)
class ZoneElectriqueAdmin(admin.ModelAdmin):
    list_display = ['name', 'zone_type', 'latitude', 'longitude', 'radius_km', 'is_active']
    list_filter = ['zone_type', 'is_active']
    search_fields = ['name']
    ordering = ['name']


@admin.register(ElectriciteSignalement)
class ElectriciteSignalementAdmin(admin.ModelAdmin):
    list_display = ['zone', 'status', 'load_level', 'source_type', 'duration_estimate_minutes', 'timestamp', 'approval_count', 'is_expired', 'ip']
    list_filter = ['status', 'load_level', 'source_type', 'timestamp', 'zone__zone_type']
    search_fields = ['zone__name', 'ip', 'comment']
    readonly_fields = ['timestamp', 'approval_count', 'ip', 'is_expired', 'comment']
    ordering = ['-timestamp']

    def is_expired(self, obj):
        return obj.is_expired()


@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    """Admin interface for Signalement model"""
    list_display = ['station', 'fuel_type', 'status', 'timestamp', 'approval_count', 'is_expired', 'ip']
    list_filter = ['fuel_type', 'status', 'timestamp', 'station__brand']
    search_fields = ['station__name', 'station__brand', 'ip', 'comment']
    readonly_fields = ['timestamp', 'approval_count', 'ip', 'is_expired', 'comment']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Signalement', {
            'fields': ('station', 'fuel_type', 'status', 'comment')
        }),
        ('Métadonnées', {
            'fields': ('timestamp', 'approval_count', 'ip', 'is_expired'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['delete_expired_signalements']
    
    def is_expired(self, obj):
        """Affiche si le signalement est expiré"""
        return obj.is_expired()
    
    is_expired.boolean = True
    is_expired.short_description = 'Expiré ?'
    
    def delete_expired_signalements(self, request, queryset):
        """Supprime les signalements expirés"""
        expired = [s for s in queryset if s.is_expired()]
        count = len(expired)
        for s in expired:
            s.delete()
        self.message_user(request, f"{count} signalement(s) expiré(s) supprimé(s).")
    delete_expired_signalements.short_description = "Supprimer les signalements expirés"


# Add inline to Station admin
StationAdmin.inlines = [SignalementInline]
