from django.db import models


class TransactionRecord(models.Model):
    hash = models.CharField(max_length=255)   # priority to index this, as this is the main API
    block_number = models.BigIntegerField()
    timestamp = models.DateTimeField()   # need to index this column for fast query?
    fee = models.FloatField()

    class Meta:
        managed = False
        db_table = 'transaction_record'


class TransactionBatchRecord(models.Model):
    hash = models.CharField(max_length=255)   # priority to index this, as this is the main API
    block_number = models.BigIntegerField()
    timestamp = models.DateTimeField()   # need to index this column for fast query?
    fee = models.FloatField()

    class Meta:
        managed = False
        db_table = 'transaction_batch_record'


class TransactionUniswapPrice(models.Model):
    hash = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    price = models.TextField()

    class Meta:
        managed = False
        db_table = 'transaction_uniswap_price'
