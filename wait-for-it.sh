#!/usr/bin/env bash
# wait-for-it.sh: ждет доступности TCP-порта
# https://github.com/vishnubob/wait-for-it

host="$1"
shift
port="$1"
shift

while ! nc -z "$host" "$port"; do
  echo "Ожидание доступности $host:$port..."
  sleep 1
done

exec "$@"
