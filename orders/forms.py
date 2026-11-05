from datetime import time
from zoneinfo import ZoneInfo
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import OrderRequest


class QuickOrderForm(forms.ModelForm):
    class Meta:
        model = OrderRequest
        fields = ["contact_phone", "pickup_time", "instructions"]
        widgets = {
            "pickup_time": forms.TimeInput(attrs={"type": "time"}),
            "instructions": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "w-full px-4 py-2 text-sm border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
                }
            )

    def clean_pickup_time(self):
        pickup_time = self.cleaned_data.get("pickup_time")
        if pickup_time:
            if pickup_time < time(8, 0) or pickup_time > time(16, 30):
                raise ValidationError(
                    "Pickup time must be during shop operating hours (8:00 AM - 4:30 PM)."
                )
        return pickup_time

    def clean(self):
        cleaned_data = super().clean()
        now_sl = timezone.localtime(timezone.now(), ZoneInfo("Asia/Colombo"))
        if now_sl.time() >= time(11, 0):
            raise ValidationError(
                "Quick orders for same-day pickup must be submitted before 11:00 AM (Asia/Colombo). "
                "Please choose a Scheduled Order for future dates."
            )
        return cleaned_data


class ScheduledOrderForm(forms.ModelForm):
    class Meta:
        model = OrderRequest
        fields = [
            "occasion",
            "pickup_date",
            "pickup_time",
            "contact_phone",
            "instructions",
        ]
        widgets = {
            "pickup_date": forms.DateInput(attrs={"type": "date"}),
            "pickup_time": forms.TimeInput(attrs={"type": "time"}),
            "instructions": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    "class": "w-full px-4 py-2 text-sm border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
                }
            )

    def clean_pickup_date(self):
        pickup_date = self.cleaned_data.get("pickup_date")
        now_sl = timezone.localtime(timezone.now(), ZoneInfo("Asia/Colombo"))
        if pickup_date and pickup_date <= now_sl.date():
            raise ValidationError(
                "Scheduled pickup date must be in the future (starting tomorrow)."
            )
        return pickup_date

    def clean_pickup_time(self):
        pickup_time = self.cleaned_data.get("pickup_time")
        if pickup_time:
            if pickup_time < time(8, 0) or pickup_time > time(16, 30):
                raise ValidationError(
                    "Pickup time must be during shop operating hours (8:00 AM - 4:30 PM)."
                )
        return pickup_time