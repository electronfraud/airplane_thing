FROM node:24

WORKDIR /app
COPY . .
RUN npm install
RUN npm run build

CMD ["./entrypoint.sh"]
