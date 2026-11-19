from enum import Enum


class RoleEnum(str, Enum):
    admin = "Admin"
    gerente = "Gerente"
    recepcionista = "Recepcionista"
    camareira = "Camareira"
    manutencao = "Manutencao"


class RoomStatusEnum(str, Enum):
    disponivel = "Disponivel"
    ocupado = "Ocupado"
    limpeza = "Limpeza"
    manutencao = "Manutencao"
    reservado = "Reservado"


class ReservationStatusEnum(str, Enum):
    pendente = "Pendente"
    confirmada = "Confirmada"
    checkin = "CheckIn"
    checkout = "CheckOut"
    cancelada = "Cancelada"
    noshow = "NoShow"


class PaymentMethodEnum(str, Enum):
    dinheiro = "Dinheiro"
    pix = "Pix"
    cartao_credito = "CartaoCredito"
    cartao_debito = "CartaoDebito"
    transferencia = "Transferencia"


class PaymentStatusEnum(str, Enum):
    pendente = "Pendente"
    pago = "Pago"
    estornado = "Estornado"


class HousekeepingStatusEnum(str, Enum):
    pendente = "Pendente"
    em_andamento = "EmAndamento"
    concluida = "Concluida"


class MaintenanceStatusEnum(str, Enum):
    aberta = "Aberta"
    em_andamento = "EmAndamento"
    resolvida = "Resolvida"
    cancelada = "Cancelada"


class PriorityEnum(str, Enum):
    baixa = "Baixa"
    media = "Media"
    alta = "Alta"
