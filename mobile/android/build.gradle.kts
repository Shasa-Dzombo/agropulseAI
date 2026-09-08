allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

// Fix for the camera plugin's camera_android_camerax subproject failing to
// compile: androidx.camera:camera-core (1.5.3, pulled in by the `camera`
// package) references androidx.concurrent.futures.CallbackToFutureAdapter
// in a type-use annotation, but androidx.concurrent:concurrent-futures
// isn't landing on that subproject's own compile classpath at all -
// camera-core apparently declares it compileOnly upstream, so it's never
// requested transitively, and a plain resolutionStrategy.force() (tried
// first) only resolves version conflicts among dependencies that are
// already requested somewhere - it doesn't add a brand new one. Adding it
// directly as an implementation dependency on every subproject (can't edit
// camera_android_camerax's own build.gradle - it's vendored from pub
// cache) makes sure the class is actually present. Uses plugins.withId
// rather than afterEvaluate - :app is forced to evaluate before other
// subprojects (see evaluationDependsOn above), so by the time a plain
// subprojects{afterEvaluate{}} block here would run for :app, it's
// already evaluated and afterEvaluate throws; withId fires immediately for
// an already-applied plugin instead, so evaluation order doesn't matter.
subprojects {
    plugins.withId("com.android.library") {
        dependencies.add("implementation", "androidx.concurrent:concurrent-futures:1.2.0")
    }
    plugins.withId("com.android.application") {
        dependencies.add("implementation", "androidx.concurrent:concurrent-futures:1.2.0")
    }
}

// file_picker 8.3.7 used to hardcode "compileSdk 34" directly in its own
// android/build.gradle (didn't read flutter.compileSdkVersion at all - just
// stale), which fell below what its own flutter_plugin_android_lifecycle
// dependency requires (36+). No override from this parent script could fix
// it either way - compileSdk is a write-once property in this AGP version
// (a plugins.withId callback runs too early, before file_picker's own
// "compileSdk 34" line clobbers it back down; afterEvaluate runs too late,
// "It is too late to set compileSdk - It has already been read to
// configure this project"). Real fix was upgrading file_picker to 10.3.3
// (see pubspec.yaml / mobile/CHANGELOG.md), whose upstream build.gradle
// reads flutter.compileSdkVersion like every other plugin - no gradle
// workaround needed here.

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
