from aip import AipSpeech

APP_ID = '119131130'
API_KEY = '4rA3ep1RWIcOZ54BUHfZ0EOX'
SECRET_KEY = 'mvmhmWEvXsrgyo9DAUMm5osO3lhePhhE'

client = AipSpeech(APP_ID,API_KEY,SECRET_KEY)

Text = '八百标兵奔北坡，炮兵并排北边跑'

filePath = 'output.mp3'

result = client.synthesis(Text,'zh',1,{'vol':5})
if not isinstance(result,dict):
    with open(filePath,'wb') as f:
        f.write(result)

else:
    print("error")

