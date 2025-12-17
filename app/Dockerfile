FROM node:22.21-slim

WORKDIR /app

COPY package*.json ./

RUN npm i

COPY . /app

RUN npm run build

CMD ["npm", "run", "preview"]