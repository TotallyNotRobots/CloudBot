FROM python:3.11-slim

WORKDIR /app

# install git (sometimes needed for dependencies)
RUN apt-get update && apt-get install -y git

# copy project files
COPY . .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# run the bot
CMD ["sh", "-c", "alembic upgrade heads && python -m cloudbot"]