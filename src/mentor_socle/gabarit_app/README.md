# __NOM__

Application Mentor bâtie sur [mentor-socle](../mentor-socle). Démarrage :

```powershell
uv sync
Copy-Item config\settings.example.yaml config\settings.yaml
Copy-Item config\modeles.example.yaml config\modeles.yaml
uv run mentor parent set-pin
uv run mentor check
uv run mentor serve      # http://127.0.0.1:__PORT__
```
