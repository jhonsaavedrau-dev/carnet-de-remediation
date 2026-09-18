# Carnet de remédiation

App para practicar francés de B2 a C1, construida a partir de mi diagnóstico DELF B2 de septiembre de 2026 y del programa de *Producción de Texto Académico en Francés C1.1* (Universidad de Pamplona).

**Abrir:** https://jhonsaavedrau-dev.github.io/carnet-de-remediation/

## Qué incluye

- **Recorrido Remédiation.** 23 lecciones construidas sobre los errores del diagnóstico: concordancias, preposiciones, *ce que / qu'est-ce que*, subjuntivo, carta formal, registro, conectores, conclusión del exposé, números y fechas al oído.
- **Recorrido Programme C1.1.** 26 lecciones: estructura textual (inversión, puesta de relieve, pasiva, puntuación avanzada), cohesión (reformulación, anáforas, discurso referido, causa, concesión, finalidad), texto académico (résumé, compte rendu, registro académico, citas) y las pruebas del DALF C1 (síntesis, ensayo, oral), con proyectos guiados.
- **Dictées.** 14 dictados con lectura completa, grupos dictados dos veces con la puntuación, modo examen, control de velocidad y corrección automática con nota sobre 20.
- **Accents et signes.** Más de 300 palabras para colocar é, è, ê, à, ç, ë, œ… con su pronunciación, más los pares cuyo sentido cambia con el acento.
- **Carnet y journal.** Los errores vuelven hasta dominarlos, y cada sesión queda registrada.

El progreso se guarda en el navegador de cada persona. Se puede instalar en el celular con «Agregar a la pantalla de inicio», y los audios ya escuchados funcionan sin conexión.

## Cómo está hecho

- `carnet-de-remediation.html`: la app completa en un solo archivo, sin dependencias. También se publica como artifact en claude.ai, donde además tiene corrección de textos con Claude y sincronización entre dispositivos.
- `generer-audio.py`: genera el audio con voces neuronales nativas fr-FR (Denise y Henri, mediante `edge-tts`). Agrupa los fragmentos en pocos archivos, porque el artifact admite un número limitado.
- `construire-site.py`: produce `index.html`, el manifiesto, los íconos y el service worker de esta versión web.

Los textos de los dictados y de los ejercicios son originales.
