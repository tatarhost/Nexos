# NEXUS OS

A responsive GitHub Pages workspace with GitHub Actions build workflows.

## Included
- Mobile-friendly workspace UI.
- Android APK build for Android Gradle projects.
- Java JAR and Gradle-based Minecraft mod builds.
- Windows x64 publish for .NET projects.
- GitHub Pages deployment workflow.
- Build artifacts retained for 14 days.

## Enable the website
1. Open repository **Settings → Pages**.
2. Set **Build and deployment → Source** to **GitHub Actions**.
3. Open **Actions** and check **NEXUS OS · Deploy Pages**.
4. The published URL appears in Pages settings and the deployment summary.

## Run a build
1. Upload a compatible source project into this repository.
2. Open **Actions → NEXUS Cloud Build → Run workflow**.
3. Choose a target and enter the project directory (`.` for repository root).
4. Download the artifact from the completed workflow run.

### Expected project types
- **Android:** Android Gradle project with `gradlew` and an `assembleDebug` task.
- **Java:** Gradle project with `gradlew` that creates JAR files in `build/libs`.
- **Minecraft mods:** compatible Gradle-based Forge/Fabric project with a `build` task.
- **Windows:** .NET project containing a `.csproj` file.

## Architecture limitation
GitHub Actions runners are temporary cloud build machines. They can compile, test, package and publish files, but they do not provide a persistent interactive desktop or keep arbitrary GUI apps running. A true remote desktop requires separate persistent hosting.

## Security
Do not commit passwords, access tokens, signing keys, or private credentials. Keep future secrets in GitHub Actions Secrets and grant workflows only the permissions they need.