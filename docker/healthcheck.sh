#!/usr/bin/env sh

TIMEOUT=30  # сек
START=$(date +%s)

while true; do
    # дивимося останні логи
    if docker logs test-bot 2>&1 | grep -q "Nightcore bot started successfully!"; then
        echo "Bot started successfully!"
        break
    fi

    STATUS=$(docker inspect -f '{{.State.Running}}' test-bot)
    if [ "$STATUS" != "true" ]; then
        echo "Bot container stopped unexpectedly!"
        docker logs test-bot
        exit 1
    fi

    NOW=$(date +%s)
    ELAPSED=$((NOW-START))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "Bot failed to start within $TIMEOUT seconds!"
        docker logs nightcore-bot
        exit 1
    fi

    sleep 1
done
