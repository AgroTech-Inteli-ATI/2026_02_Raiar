FROM python:3.12-slim
# Cria a pasta de dados já com o dono certo. Um volume novo herda esse dono.
RUN mkdir /dados && chown 1000:1000 /dados
WORKDIR /app
COPY app/contador.py .
USER 1000:1000
CMD ["python", "contador.py"]
