mv ~/Cobranca-Ave-Branca/credentials.env ~/
mv ~/Cobranca-Ave-Branca/AveBranca.json ~/
mv ~/Cobranca-Ave-Branca/flags.json ~/

rm -rf ~/Cobranca-Ave-Branca/

cd

git clone https://github.com/gdantas04/Cobranca-Ave-Branca

rm ~/Cobranca-Ave-Branca/credentials.env
rm ~/Cobranca-Ave-Branca/AveBranca.json
rm ~/Cobranca-Ave-Branca/flags.json

mv ~/Credentials.env ~/Cobranca-Ave-Branca
mv ~/AveBranca.json ~/Cobranca-Ave-Branca
mv ~/flags.json ~/Cobranca-Ave-Branca

echo Done!
