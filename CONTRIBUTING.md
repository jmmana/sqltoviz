# Contributing / Contribuir

## English

1. Start from `development` on a short-lived branch named `type/issue-description`. Keep the change scoped to one issue or a closely related group.
2. Open a PR to `development`. Link the issue, explain the change, and provide test commands, results, and any limits. Run the checks applicable to the changed files and resolve blocking review feedback.
3. After the checks pass, merge the PR into `development`. Close the issue once its acceptance criteria and any required deployment or installation have been verified. Delete the temporary branch after its PR is merged.
4. Promote `development` to `main` via a release PR. Wait for the applicable checks, then use the [alpha release runbook](docs/alpha-release.md) to validate any deployment or package publication.

Submit public guides in English and Spanish. Report vulnerabilities through the [security policy](SECURITY.md).

## Español

1. Crea una rama temporal desde `development` con el nombre `tipo/issue-descripción`. Limita el cambio a un issue o a un grupo estrechamente relacionado.
2. Abre un PR hacia `development`. Enlaza el issue, explica el cambio e incluye comandos de prueba, resultados y limitaciones. Ejecuta las verificaciones aplicables y resuelve las observaciones que impidan fusionar.
3. Cuando pasen las verificaciones, fusiona el PR en `development`. Cierra el issue cuando se cumplan sus criterios de aceptación y se haya verificado cualquier despliegue o instalación exigidos. Elimina la rama temporal después de fusionar su PR.
4. Promueve `development` a `main` mediante un PR de lanzamiento. Espera las verificaciones aplicables y utiliza la [guía de lanzamiento alfa](docs/alpha-release.md) para validar cualquier despliegue o publicación de paquetes.

Entrega las guías públicas en inglés y español. Reporta vulnerabilidades según la [política de seguridad](SECURITY.md).
