# Importando o módulo
import telebot, json, time, os, mercadopago, datetime
from datetime import date
from threading import Thread
from telebot import types
from dotenv import load_dotenv 


# Carrega tokens e ids da variavel de ambiente credentials.env
load_dotenv(dotenv_path= f'{os.getcwd()}/credentials.env') 
mPagoToken = os.getenv("mPagoToken")
telebotToken = os.getenv("telebotToken")
tesAccount = int(os.getenv("tesId"))



# Implementação do pagamento (gera pix e verifica se houve pagamento)
class Payment():
    def __init__(self):
        self.id = None
        self.sdk = mercadopago.SDK(mPagoToken)
        self.moment_of_payment = None


    def Pay(self, amount, description):

        payment_data = {
            "transaction_amount": amount,
            "description": f"{description}",
            "payment_method_id": 'pix',
            "installments": 1,
            "payer": {
                "email": 'abc@123.com'
            }
        }

        self.id = self.sdk.payment().create(payment_data)["response"]["id"]
        pixCode = self.sdk.payment().get(self.id)["response"]['point_of_interaction']['transaction_data']['qr_code']

        self.moment_of_payment = datetime.datetime.now()

        return pixCode

    def paymentStatus(self):
        if self.id is not None:
            return self.sdk.payment().get(self.id)["response"]["status"]


    def polling(self, minutes=10):
        while(((datetime.datetime.now() - self.moment_of_payment).seconds)/60 < minutes):
            if self.paymentStatus() == 'approved':
                return self.paymentStatus()
            else:
                time.sleep(2)
        else:
            self.sdk.payment().update(self.id, {"status": "cancelled"})
            return self.paymentStatus()

# Implementação do banco de dados de usuários
class Database():
    def __init__(self, file):
        self.file = file
        self.database = None

        
    def getDatabase(self):
        with open(self.file) as f:
            self.database = json.load(f)

        return self.database

    def addUser(self, telegram_id=None, name=None):
        with open(self.file) as f:
            self.database = json.load(f)

        if str(telegram_id) not in self.database.keys():
        
            self.database[telegram_id] =   {"name" : name, "payments" : {}}
                                    
            with open(self.file, 'w') as f:
                json.dump(self.database, f)

    def removeUser(self, telegram_id):
        with open(self.file) as f:
            self.database = json.load(f)

        if str(telegram_id) in self.database.keys():
        
            self.database.pop(str(telegram_id))
                                    
            with open(self.file, 'w') as f:
                json.dump(self.database, f)



    def updatePaymentStatus(self, telegram_id, month, payment=None):
        with open(self.file) as f:
            self.database = json.load(f)

        self.database[str(telegram_id)]["payments"][month] = payment

        with open(self.file, 'w') as f:
            json.dump(self.database, f)


    def getPendingUsers(self):
        with open(self.file) as f:
            self.database = json.load(f)

        pendent = {}

        for user_id in self.database:
            flag = False
            aux_list = []
            for payment in self.database[user_id]["payments"]:
                if self.database[user_id]["payments"][payment] == 0:
                    flag = True
                    aux_list.append(payment)

            if flag == True:
                pendent[int(user_id)] = aux_list

        return pendent

# Registro das flags do envio de mensagens no dia 5 e no dia 15
class sent_flag():
    def __init__(self, file):
        self.file = file
        self.flag5 = None
        self.flag15 = None
        self.flags = None

    def getFlag(self, num):
        with open(self.file) as f:
            if num == 5:
                self.flag5 = json.load(f)["5"]
                return self.flag5
            
            if num == 15:
                self.flag15 = json.load(f)["15"]
                return self.flag15


    def writeFlag(self, day, flag):
        with open(self.file) as f:
            self.flags = json.load(f)

        self.flags[str(day)] = flag

        with open(self.file, 'w') as f:
            json.dump(self.flags, f)


# Carregar banco de dados como usersData
usersData = Database('AveBranca.json') 

# Preço da mensalidade
subscription = 15

# Flags de registro do dia 5 e/ou dia 15
flags = sent_flag('flags.json')

# Datas de cobrança;
start_date = 5
end_date = 15 

# Bot Token
bot = telebot.TeleBot(telebotToken)



# Botões que aparecem para o membro comum
markup = types.ReplyKeyboardMarkup(one_time_keyboard=False)
markup.add('/pendencias', '/pagar')

# Botões que aparecem para a conta da tesouraria
markup_tes = types.ReplyKeyboardMarkup(one_time_keyboard=False)
markup_tes.add('/gestao', '/remove')

# Botão que aparecem para o usuario que inseriu um nome inválido
markup_unregistered = types.ReplyKeyboardMarkup(one_time_keyboard=True)
markup_unregistered.add('/start')



# Função que realiza o backup do banco de dados todos os dias às 18:00
def scheduleBackup():
    while True:
        if time.strftime("%H:%M") == "18:00":

            tocp_file = f'{os.getcwd()}/AveBranca.json'
            out_file = f'{os.getcwd()}/bup-{time.strftime("%D").replace("/","-")}.json'

            os.system(f'cp  {tocp_file} {out_file}')

            bot.send_document(tesAccount, open(out_file, 'rb'))
            
            os.system(f'rm {out_file}')
            
            time.sleep(120)
        else:
            time.sleep(5)


# Função que lembra os usuários de fazerem o pagamento
def requestPayment():
    try:
        while True:
            if (date.today().day == start_date) and (flags.getFlag(5) == False):
                bot.send_message(tesAccount, f'Os pagamentos abriram hoje ({start_date}) e os membros devedores estão sendo informados.', reply_markup=markup_tes)
                for user_id in usersData.getDatabase():
                    bot.send_message(int(user_id), f"🫵 Olá! Hoje é dia {start_date}, e você já pode pagar a sua mensalidade. Não deixe pra outra hora e emita o pix com o comando /pagar.", reply_markup=markup)
                    month = f'{date.today().month}/{date.today().year}'
                    usersData.updatePaymentStatus(int(user_id), month, 0)

                flags.writeFlag(5, True)

            if (date.today().day != start_date) and (flags.getFlag(5) == True):
                flags.writeFlag(5, False)



            if (date.today().day == end_date) and (flags.getFlag(15) == False):
                bot.send_message(tesAccount, f'Hoje é o prazo máximo de pagamento ({end_date}) e os membros devedores estão sendo informados.', reply_markup=markup_tes)

                for user in usersData.getPendingUsers():
                    text = ''
                    for pend in usersData.getPendingUsers()[user]:
                        text += f'{pend}\n'
                    bot.send_message(user, f"🫵 Olá! Estou passando para lembrar da sua mensalidade. Hoje é o prazo máximo para efetuar o pagamento. Seguem as suas pendências:\n\n{text}", reply_markup=markup)
                flags.writeFlag(15, True)

            if (date.today().day != end_date) and (flags.getFlag(15) == True):
                flags.writeFlag(15, False)

            time.sleep(5)
    
    except Exception:
        pass




def commands():

    # Comando /start (cadastra novos usuários)
    @bot.message_handler(commands=['start'])
    def start(message):
        try:
            if usersData.getDatabase() == None or str(message.from_user.id) not in usersData.getDatabase() and message.from_user.id != tesAccount:
                name = bot.send_message(message.from_user.id, '😃 Parece que é sua primeira vez aqui...\n\nMe informe seu nome completo para eu criar seu cadastro.')
                bot.register_next_step_handler(name, startResp)
            else:
                if message.from_user.id == tesAccount:
                    bot.send_message(message.from_user.id, f'Você já está cadastrado!', reply_markup=markup_tes)
                else:
                    bot.send_message(message.from_user.id, f'👋 Olá novamente!', reply_markup=markup)
        except Exception:
            bot.send_message(message.from_user.id, 'Oops...')

    def startResp(message):
        try:
            name = message.text
            if str(name).replace(' ','').isalpha():
                usersData.addUser(message.from_user.id, name)
                bot.send_message(message.from_user.id, f'🤝 {name} foi adicionado ao banco de dados.', reply_markup=markup)
                bot.send_message(tesAccount, f'{name} foi adicionado ao banco de dados.', reply_markup=markup_tes)
            else:
                bot.send_message(message.from_user.id, f'❌ "{name}" não é um nome válido.\n\nExecute /start para refazer seu cadastro.', reply_markup=markup_unregistered)

        except Exception:
            bot.send_message(message.from_user.id, 'Oops...')

            

    # Comando /gestao (mostra usuarios devedores e quantos estão cadastrados) - disponivel apenas para a tesouraria
    @bot.message_handler(commands=['gestao'])
    def gestao(message):
        try:
            if message.from_user.id == tesAccount:

                pendent_txt = f'{len(usersData.getDatabase())} usuários cadastrados\n\n\n'
                for pendent in usersData.getPendingUsers():
                    aux = ''
                    for _ in usersData.getPendingUsers()[pendent]:
                        aux += f'{_}\n'
                    pendent_txt += f'{usersData.getDatabase()[str(pendent)]["name"]} deve R$ {subscription*len(usersData.getPendingUsers()[pendent]):.2f} dos meses:\n{aux}\n\n'

                bot.send_message(message.from_user.id, pendent_txt, reply_markup=markup_tes)

        except Exception:
            bot.send_message(message.from_user.id, 'Oops...')


    # Comando /remove (remove usuário pelo id)
    @bot.message_handler(commands=['remove'])
    def remove(message):
        try:
            if message.from_user.id == tesAccount:
                if len(usersData.getDatabase()) > 0:
                    users_txt = 'DIGITE O ID A SER REMOVIDO:\n\n\n'
                    for user_id in usersData.getDatabase():
                        users_txt += f'ID: {user_id}\nNOME: {usersData.getDatabase()[user_id]["name"]}\n\n'

                    to_remove = bot.send_message(tesAccount, users_txt)

                    bot.register_next_step_handler(to_remove, removeResp)
                else:
                    bot.send_message(tesAccount, "Não há usuários a serem removidos.")
        except Exception:
            bot.send_message(message.from_user.id, 'Oops...')

    def removeResp(message):
        try:
            to_remove = message.text
            if to_remove in usersData.getDatabase():
                usersData.removeUser(to_remove)
                bot.send_message(tesAccount, f'{to_remove} foi removido do banco de dados.', reply_markup=markup_tes)
            else:
                bot.send_message(tesAccount, 'Verifique o ID informado e tente novamente.', reply_markup=markup_tes)
        except Exception:
            bot.send_message(message.from_user.id, 'Oops...')



    # Comando /pendencias (mostra pendencias, caso existam)
    @bot.message_handler(commands=['pendencias'])
    def pendencias(message):
        try:
            if str(message.from_user.id) in usersData.getDatabase():
                try:
                    text = ''
                    to_pay = 0
                    for pend in usersData.getPendingUsers()[message.from_user.id]:
                        to_pay += subscription
                        text += f'{pend}\n'
                    bot.send_message(message.from_user.id, f'👀 Você está devendo R$ {to_pay},00 dos seguintes meses:\n\n{text}', reply_markup=markup)
                except Exception:
                    bot.send_message(message.from_user.id, '🙏 Você não tem pendências.', reply_markup=markup)
        except Exception:
            bot.send_message(message.from_user.id, 'Oops...')
                    

    # Comando /pagar (efetua o pagamento)
    @bot.message_handler(commands=['pagar'])
    def pagar(message):
        try:
            if message.from_user.id in usersData.getPendingUsers():

                confirmation = bot.send_message(message.from_user.id, '''❗️ Digite: "quero pagar" para gerar seu código pix (ele tem validade de 5 minutos).''')
                bot.register_next_step_handler(confirmation, fazerPagamento)

            else:
                bot.send_message(message.from_user.id, '🙏 Você não tem pagamentos a serem feitos.', reply_markup=markup)
        except Exception:
            bot.send_message(message.from_user.id, 'Oops...')


    def fazerPagamento(message):
        try:
            confirmation = message.text

            if confirmation == "quero pagar":
                to_pay = f'{len(usersData.getPendingUsers()[message.from_user.id])*subscription:.2f}'

                identifier = f'm{date.today().month}y{date.today().year}id{message.from_user.id}'

                payment = Payment()
                payload = payment.Pay(float(to_pay), identifier)


                bot.send_message(message.from_user.id, f'⚔️ Faça o pagamento de R${to_pay.replace(".",",")} através do código abaixo. O valor é relativo ao mês atual e às pendências, caso hajam.\n\n⚠️ NOTA: VOCÊ TEM 5 MINUTOS A PARTIR DE AGORA PARA FAZER O PAGAMENTO.', reply_markup=markup)
                bot.send_message(message.from_user.id, f'<code>{payload}</code>', parse_mode='HTML',reply_markup=markup)

                
                status = payment.polling()

                if status == 'approved':
                    bot.send_message(message.from_user.id, '✅ Seu pagamento foi aprovado!', reply_markup=markup)

                    for pend in usersData.getPendingUsers()[message.from_user.id]:
                        usersData.updatePaymentStatus(message.from_user.id, pend, 1)

                    bot.send_message(tesAccount, f'Pagamento de R$ {to_pay} enviado por {usersData.getDatabase()[str(message.from_user.id)]["name"]}.', reply_markup=markup_tes) #Envia o pagamento ao tesoureiro

                else:
                    bot.send_message(message.from_user.id, '❌ Seu pagamento não foi validado.\n\nSe você acha que isso foi um engano, contate a tesouraria.', reply_markup=markup)

            else:
                bot.send_message(message.from_user.id, "❌ Solicitação inválida.", reply_markup=markup)
        
        except Exception:
            bot.send_message(message.from_user.id, 'Oops...')



# Threads pra fazer os comandos ficarem plenamente executaveis enquanto é feita a verificação de data
try:
    Thread(target = commands).start()
except Exception():
    exit()

try:
    Thread(target = requestPayment).start()
except Exception():
    exit()

try:   
    Thread(target = scheduleBackup).start()
except Exception():
    exit()

try:
    bot.infinity_polling()
except Exception():
    exit()
