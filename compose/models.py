from django.db import models

class Session(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    theme = models.CharField(max_length=120, blank=True)
    season_hint = models.CharField(max_length=30, blank=True)
    def __str__(self): return f"Session {self.id}: {self.theme}"

class Draft(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="drafts")
    version = models.PositiveIntegerField()
    text = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"v{self.version}: {self.text[:20]}"

class Move(models.Model):
    MOVE_CHOICES=[("seed","種"),("word_add","語追加"),("word_del","語削除"),("kire","切れ"),("imagery","造形"),("note","メモ")]
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="moves")
    draft = models.ForeignKey(Draft, on_delete=models.SET_NULL, null=True, blank=True, related_name="moves")
    kind = models.CharField(max_length=16, choices=MOVE_CHOICES)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

class RubricSnapshot(models.Model):
    draft = models.OneToOneField(Draft, on_delete=models.CASCADE, related_name="rubric")
    total = models.FloatField()
    breakdown = models.JSONField()
    triplet = models.CharField(max_length=20)
