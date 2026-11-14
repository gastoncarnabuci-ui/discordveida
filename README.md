# Discord Answer Bot

Bot de Discord en Python que responde en español con humor seco y sarcástico. Usa una personalidad original de supercomputadora de ciencia ficción; no imita a Ultrón ni a otro personaje.

## Qué hace

- Responde a `/preguntar`.
- También responde cuando alguien lo menciona en un mensaje.
- Mantiene un contexto breve separado por usuario y canal. El historial solo vive mientras el proceso está encendido.
- Prioriza respuestas correctas y admite cuando no sabe. No tiene navegación web ni puede garantizar que cada respuesta sea correcta.
- Evita pings involuntarios en las respuestas y limita la frecuencia de preguntas por usuario.
- Envía la pregunta y su contexto breve a Google Gemini (`gemini-2.5-flash`) para generar la respuesta.

## Configuración en Replit

Los siguientes valores deben guardarse en **Secrets**, nunca en el código ni en archivos `.env`:

- `DISCORD_BOT_TOKEN`: token del bot creado en Discord Developer Portal.
- `GEMINI_API_KEY`: clave de Google Gemini. Las solicitudes están sujetas a la cuota y facturación del proyecto asociado a esa clave.

Opcional:

- `DISCORD_GUILD_ID`: ID numérico de un servidor de pruebas. Si se configura, `/preguntar` se sincroniza allí para probarlo más rápido. Sin este valor, se sincroniza como comando global y Discord puede tardar en mostrarlo.

## Crear e invitar el bot

1. En Discord Developer Portal, crea una aplicación y añade un usuario de bot.
2. Copia el token del bot directamente a Replit Secrets como `DISCORD_BOT_TOKEN`. No lo publiques ni lo pegues en un canal.
3. En **Bot → Privileged Gateway Intents**, habilita **Message Content Intent** para que el bot pueda leer las preguntas de los mensajes que lo mencionan.
4. En **OAuth2 → URL Generator**, selecciona los ámbitos `bot` y `applications.commands`.
5. Dale solo los permisos necesarios: ver canales, enviar mensajes, leer el historial y usar comandos de aplicación. Abre el enlace generado e invita el bot a tu servidor.
6. Añade `GEMINI_API_KEY` en Replit Secrets.

## Ejecutar

El workflow **Discord Bot** mantiene el bot conectado. También puedes iniciarlo con:

```bash
uv run python -m discord_bot
```

Si usas un servidor de pruebas, configura `DISCORD_GUILD_ID` como variable de entorno normal y reinicia el workflow. No compartas ninguno de los tokens.
