# Changelog / Registro de cambios

## Version policy / Política de versiones

The SDKs share one release sequence. Use SemVer for npm and NuGet and the
equivalent PEP 440 version for Python. For example, `0.1.0-alpha.1` maps to
`0.1.0a1`. Keep the version of the response and feature contracts independent of
the package version. Record changes to those contracts and migration steps here.

Los SDK comparten una secuencia de lanzamientos. Usa SemVer para npm y NuGet y
su equivalente PEP 440 para Python. Por ejemplo, `0.1.0-alpha.1` corresponde a
`0.1.0a1`. Versiona los contratos de respuesta y características por separado.
Registra aquí los cambios en esos contratos y los pasos de migración.

For each release, move the applicable entries from **Unreleased** into a version
section and add the publication date once all three registries are verified.
Record breaking changes, features, fixes and known limitations. Follow the
[release runbook](docs/alpha-release.md). Increment the alpha counter for changes
after a prerelease has been published.

Para cada lanzamiento, mueve las entradas correspondientes de **Unreleased** a
una sección de versión y agrega la fecha de publicación cuando se verifiquen los
tres registros. Documenta cambios incompatibles, funcionalidades, correcciones
y limitaciones. Sigue la [guía de lanzamiento](docs/alpha-release.md). Incrementa
el contador alfa para cambios posteriores a una publicación preliminar.

## Unreleased / Sin publicar

### First alpha / Primera alfa

| SDK | Package / Paquete | Version / Versión |
| --- | --- | --- |
| Python | `sqltoviz` | `0.1.0a1` |
| npm | `@sqltoviz/core` | `0.1.0-alpha.1` |
| NuGet | `SqlToViz` | `0.1.0-alpha.1` |

- Local rule-based SQL result preview and shared preview parity fixtures.
- Vista previa local basada en reglas para resultados SQL, con casos de paridad compartidos.
- Scope is limited to the deterministic preview. Candidate ONNX models remain experimental.
- El alcance se limita a la vista previa determinista. Los modelos ONNX candidatos siguen siendo experimentales.
