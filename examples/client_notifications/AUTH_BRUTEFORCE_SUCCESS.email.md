<!--
Ejemplo ilustrativo, renderizado a partir de AUTH_BRUTEFORCE_SUCCESS.output.json.
No es un correo real enviado -- este repo no implementa envío de correo (ver README.md).
-->

**Asunto:** [KRP-2026-000481] CRÍTICO — Entraron a su Servidor de facturación

---

Estimado(a) responsable:

**NIVEL DE ATENCIÓN: Crítico**

**Qué pasó:** El 14 de julio a las 3:23 p. m. alguien entró a su Servidor de facturación con la cuenta administrador.

**Por qué importa:** Es muy probable que la contraseña de esa cuenta esté ahora en manos de un intruso.

**Lo que detectamos:** 10 intentos de acceso fallidos desde una misma dirección de internet, y minutos después un acceso **exitoso** desde esa misma dirección usando la cuenta administrador. El equipo afectado es su Servidor de facturación, un activo crítico para su operación.

**Qué debe hacer usted:**
- Cambie de inmediato la contraseña de la cuenta administrador desde otro equipo.
- Si esa misma contraseña se usa en otros servicios, cámbiela también ahí.
- Confirme si alguien de su equipo o su soporte de TI accedió legítimamente en ese horario.

**Qué NO debe hacer:** No apague el servidor: se pierde el rastro de lo que hizo el intruso después de entrar.

**Qué está haciendo Kriptome:** Estamos revisando qué hizo esa cuenta después de entrar. Con su autorización, podemos bloquear la dirección de origen.

**Cómo responder:** Responda este mismo correo (sin cambiar el asunto) indicando:
- si reconoce esta actividad,
- quién la realizó y por qué,
- qué acciones ya tomó usted,
- y si notó algo más fuera de lo normal en ese equipo.

---

Equipo Kriptome · Monitoreo de seguridad
Este correo es sobre el caso KRP-2026-000481. Kriptome nunca le pedirá contraseñas, pagos ni instalar programas. Ante cualquier duda, llámenos al (01) 6XX XXXX.

**Detalle para su soporte técnico:** dirección de origen 198.51.100.23 · cuenta administrador · equipo AST-004 (srv-facturacion-01.cli001.local) · regla Kriptome 100013 · MITRE T1110/T1078 · caso KRP-2026-000481. *Nota de evidencia: el conteo de 10 intentos fallidos corresponde a la misma dirección IP, no verificado evento-por-evento contra la cuenta administrador — por eso el mensaje separa "intentos desde la misma dirección" del "acceso exitoso con la cuenta administrador".*
