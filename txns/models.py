from django.db import models


class TransactionRecord(models.Model):
    hash = models.CharField(max_length=255)   # priority to index this, as this is the main API
    block_number = models.IntegerField()   # need to index this column for fast query?
    fee = models.FloatField()

    class Meta:
        managed = False
        db_table = 'transaction_record'
