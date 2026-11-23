# 🚀 Poner Jarvis online (en Render)

Esta guía te lleva de cero a tener Jarvis en una dirección de internet que abrís desde el celular. Está escrita para hacerlo por primera vez: seguila en orden y no te saltees la parte de seguridad.

> **Una advertencia honesta.** Poner algo online no es lo mismo que correrlo en tu PC. Cualquiera que encuentre la dirección puede intentar entrar, y detrás hay una IA de pago. Por eso Jarvis pide contraseña, bloquea los intentos repetidos y tiene un tope de mensajes por día, pero **la red de seguridad más importante la ponés vos**: el tope de gasto en la cuenta de Anthropic (Paso 1).

## Lo que vas a necesitar

| Cosa | Para qué | Dónde |
|---|---|---|
| Tu código en GitHub, en la rama `main` | Render lo lee de ahí | Ya lo tenés |
| Una cuenta en Anthropic con una **clave de la API** | Es el cerebro de Jarvis online | Consola de la API de Anthropic |
| Una cuenta en Render | Es donde corre Jarvis | render.com (entrá con tu usuario de GitHub) |
| Tu PC, 10 minutos y esta guía | | |

Crear las cuentas, aceptar términos, cargar una tarjeta y pegar tus claves lo hacés **vos**. Yo no creo cuentas ni toco tus claves.

---

## Paso 1: la clave de la API de Claude (y su tope de gasto)

1. Entrá a la consola de la API de Anthropic (platform.claude.com; si la dirección cambió, buscala desde la documentación de la API) y creá una cuenta o iniciá sesión.
2. **Fijá un tope de gasto mensual** en la sección de límites o facturación. Elegí un número con el que estés cómodo (por ejemplo, unos pocos dólares). Es tu red de seguridad principal: si algo sale mal, el gasto se corta ahí.
3. Creá una **clave de la API** y copiala en el momento (después no se vuelve a mostrar). Tratala como una contraseña: **no la pegues en el código, ni en GitHub, ni en un chat**.
4. Probala en tu PC con un solo pedido chiquito (cuesta una fracción de centavo). En PowerShell, dentro de la carpeta de Jarvis:

```powershell
$env:ANTHROPIC_API_KEY = "tu-clave"
python probar_claude.py
```

Si dice `OK. Jarvis contestó: …`, la clave anda. Si dice `FALLÓ`, el mensaje te explica qué pasó (clave inválida, sin crédito, etc.).

## Paso 2: generá tu contraseña y tu perfil

```powershell
python generar_claves.py
```

Te imprime dos cosas, **solo en la pantalla** (no guarda nada):

- **Una contraseña de entrada** al azar. Podés usar otra, pero larga y única. Guardala en tu gestor de contraseñas.
- **Tu perfil en una línea** (sale de tu `perfil.json`). Es lo que le dice a Jarvis cómo te llamás y qué te gusta.

Dejá esa ventana abierta: en el próximo paso las copiás a Render.

## Paso 3: crear el servicio en Render

1. Entrá a render.com e iniciá sesión con GitHub.
2. Elegí **New** y después **Blueprint**. Conectá tu repositorio `jarvis` y elegí la rama `main`.
3. Render encuentra el archivo `render.yaml` y te muestra el servicio **jarvis**. Te va a pedir tres valores secretos:
   - `JARVIS_PASSWORD`: la contraseña del Paso 2.
   - `ANTHROPIC_API_KEY`: tu clave del Paso 1.
   - `JARVIS_PROFILE`: la línea de perfil del Paso 2.
4. Confirmá. Render construye el contenedor (la primera vez tarda varios minutos).

*(Si tu pantalla se ve distinta a esta descripción, buscá la opción equivalente: los nombres de los botones pueden cambiar.)*

Las demás variables (`JARVIS_SECRET`, `JARVIS_COOKIE_SECURE`, `JARVIS_DAILY_LIMIT`) ya vienen resueltas en `render.yaml`.

## Paso 4: abrirlo desde el celular

1. Cuando el despliegue termine, Render te da una dirección tipo `https://jarvis-xxxx.onrender.com`. Probá primero `…/api/health` en cualquier navegador: debe mostrar `{"ok":true}`.
2. Abrí la dirección en el celular, entrá con tu contraseña y escribile algo.
3. **iPhone:** abrilo en **Safari** (el reconocimiento de voz de la página anda ahí). La primera vez que toques 🎤, Safari te pide permiso para el micrófono. Si el micrófono falla, probá el **dictado del teclado** (el micrófono del teclado del iPhone), que es más confiable. Para dictar tiene que estar activado en *Ajustes → General → Teclado → Activar dictado*.
4. Opcional: *Compartir → Agregar a pantalla de inicio* para tener un ícono.

---

## Qué esperar del plan gratis (y cuándo pasar a uno de pago)

El plan gratis es para **probar**:

- **Se duerme** a los 15 minutos sin uso y tarda cerca de un minuto en despertar. Si abrís la página y tarda, es eso.
- **No guarda archivos.** Cuando se duerme o se reinicia, se pierden las **notas, la memoria y los recordatorios**.
- Mientras duerme, los recordatorios no suenan. Al despertar, los que vencieron te los avisa.

Si lo vas a usar en serio, pasalo a un plan de pago y agregale un disco:

1. En el servicio **jarvis**, cambiá el tipo de instancia a uno de pago (el más chico alcanza). Los planes de pago no se duermen.
2. En la sección de **Disks**, agregá un disco con ruta de montaje **`/data`** (con 1 GB sobra). Jarvis ya está configurado para guardar ahí sus datos (`JARVIS_DATA_DIR=/data`).
3. Render reinicia el servicio. Desde ahí, tus notas, tu memoria y tus recordatorios sobreviven.

Un servicio con disco no se puede escalar a varias instancias, y eso está bien: Jarvis guarda su estado en memoria y necesita ser una sola.

Los precios cambian: mirá la página de precios de Render antes de elegir.

## Seguridad: la lista de control

- [ ] **Tope de gasto** fijado en la cuenta de Anthropic.
- [ ] **Contraseña larga y única** (la que generó `generar_claves.py` sirve).
- [ ] **Ningún secreto en GitHub.** Las claves, la contraseña y el perfil viven solo en el panel de Render. El archivo `render.yaml` los declara pero no tiene sus valores.
- [ ] **No actives `ANTHROPIC_LOG=debug`** en Render: ese modo registra el contenido de tus mensajes.
- [ ] Revisá de vez en cuando el uso en la consola de Anthropic.
- [ ] **Si sospechás que se filtró algo:** borrá la clave de la API en la consola de Anthropic y creá otra; cambiá `JARVIS_PASSWORD` y `JARVIS_SECRET` en Render (cambiar `JARVIS_SECRET` cierra todas las sesiones abiertas).
- [ ] Compartí la dirección solo con quien confíes. La contraseña protege, pero no hace falta que la dirección ande dando vueltas.

Lo que Jarvis ya hace por vos: entra solo con contraseña; 5 intentos fallidos seguidos bloquean esa IP por 15 minutos; la sesión es una cookie que JavaScript no puede leer y que solo viaja por HTTPS; el servidor corre sin permisos de administrador; y tiene un tope de 300 mensajes por día (`JARVIS_DAILY_LIMIT`) y de 20 por minuto.

## Si algo falla

| Qué ves | Qué pasa | Qué hacer |
|---|---|---|
| La página tarda mucho en abrir | El plan gratis estaba dormido | Esperá cerca de un minuto |
| El despliegue falla y en los registros dice `JARVIS_BRAIN=claude necesita la variable ANTHROPIC_API_KEY` | Falta la clave de la API | Cargala en las variables del servicio |
| El despliegue falla y dice `Definí la variable JARVIS_PASSWORD` | Falta la contraseña, o tiene menos de 10 caracteres | Cargala (10 caracteres o más) |
| Jarvis te llama "Tu nombre" | `JARVIS_PROFILE` falta o no es un JSON válido | Volvé a copiar la línea que imprime `generar_claves.py` |
| "…la clave de la API no anda" | Clave mal copiada o borrada | Revisá `ANTHROPIC_API_KEY` |
| "Se acabó el crédito de la API" | Sin saldo, o llegaste al tope | Revisá la facturación en la consola de Anthropic |
| "Por hoy ya fue, llegamos al tope de mensajes" | Se usó el tope diario | Mañana sigue, o subí `JARVIS_DAILY_LIMIT` |
| Se perdieron las notas | Plan gratis o sin disco | Pasá a un plan de pago con disco en `/data` |
| "Demasiados intentos" al entrar | 5 contraseñas malas seguidas | Esperá 15 minutos |

Los registros (logs) del servicio están en el panel de Render. Ahí se ve el modelo, la cantidad de tokens y los errores, pero **nunca** tus mensajes ni tu clave.

## Apagarlo o borrarlo

- **Pausarlo:** suspendé el servicio en Render. No cobra y no responde.
- **Borrarlo del todo:** borrá el servicio en Render y la clave de la API en la consola de Anthropic.
