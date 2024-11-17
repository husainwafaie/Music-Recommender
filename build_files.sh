# build_files.sh
pip install -r requirements.txt
python musicrecommender/manage.py collectstatic --noinput