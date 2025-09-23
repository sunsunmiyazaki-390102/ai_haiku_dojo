from django import forms

class SessionForm(forms.Form):
    odai = forms.CharField(
        label="お題",
        max_length=160,
        required=True,
        help_text="例：『初秋／古道に響く下駄の音』『兼題：月』『写真URL』など何でもOK",
        widget=forms.TextInput(attrs={"class":"w-full p-2 border rounded"})
    )

class DraftForm(forms.Form):
    text = forms.CharField(
        label="俳句",
        max_length=60,
        widget=forms.TextInput(attrs={"class":"w-full p-2 border rounded","placeholder":"花の雨/橋のたもとに/足音や"})
    )
