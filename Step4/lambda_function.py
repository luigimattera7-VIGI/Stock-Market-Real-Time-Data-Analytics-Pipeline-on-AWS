import boto3
import os

sns = boto3.client('sns')
# Asegúrate de que este ARN sea el correcto
SNS_TOPIC_ARN = 'TU_SNS_TOPIC_ARN'  # Reemplaza con tu ARN real del SNS
TARGET_PRICE = 850.0  # Cambia esto al precio objetivo que desees

def lambda_handler(event, context):
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            new_image = record['dynamodb']['NewImage']
            price = float(new_image['price']['N'])
            symbol = new_image['symbol']['S']
            
            # --- Lógica de Precio Objetivo ---
            if price <= TARGET_PRICE:
                message = f"ALERTA DE PRECIO: {symbol} ha alcanzado el objetivo de {TARGET_PRICE}. Precio actual: {price}"
                sns.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject="Precio Objetivo Alcanzado")

            # --- Lógica de Tendencias (Simulación simplificada) ---
            # Nota: En un entorno real, aquí deberías consultar los últimos 20 registros
            # de DynamoDB para calcular las SMA reales.
            # Para esta prueba, si el precio sube bruscamente:
            print(f"Procesando {symbol} a {price}")
            
    return {'statusCode': 200}