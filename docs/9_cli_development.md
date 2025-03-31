## How to Install the Library

Once you have cloned the repo, you can install it locally with `pip`:

```bash
pip install -e ".[dev]"
```

### Why `-e`?
The `-e` flag is optional and stands for "editable mode." This allows you to make changes to the source code of the library and have those changes reflected immediately without needing to reinstall the dependency package. This is useful for development purposes.
---


## How to Build the distributable Package

To build the package, use [Hatch](https://hatch.pypa.io/latest/), a modern Python project management tool. Follow these steps:

1. **Install Hatch**  
   If you don’t already have Hatch installed, install it using `pip`:

   ```bash
   pip install hatch
   ```

2. **Build the Package**  
   Navigate to the root directory of the project and run:

   ```bash
   hatch build
   ```

   This will create the distribution files (e.g., `.whl` and `.tar.gz`) in the `dist` directory.

3. **Install the Package**  
   Once the package is built, you can install it locally:

   ```bash
   pip install dist/<filename>.whl
   ```

*(Replace `<filename>` with the actual name of the wheel file created in the `dist` directory.)*

### Running tests
You can run `hatch run test:coverage run -m pytest` to run the tests for both the CLI and SDK.


## Release process
1. In order to create a release in the wxo-clients toolchain, trigger a manual run of the "Auto Release - Patch/Minor/Major"
pipeline. 
2. This will open a `main-staging-X.Y.Z` branch. This branch will publish all commits to testpypi for QA to validate
the release. Instructions for how to use testpypi will be published as a comment on the PR.
3. When the release is cleared for release, run the "Auto Release - Release job" specifying the staging branch to release.
This will create a `main-release-X.Y.Z` branch. Upon building this branch a release will be published to pypi.
4. Merge the `main-release-X.Y.Z` PR to main. This will close both this pr and the `main-staging-X.Y.Z`. PR as they contain
the same commits.

**Fixing a release:**
- If a bug is found that causes a need to respin a release. That fix should be merged into main, and then into `main-staging-X.Y.Z`. 

**Prebuilds:**<br>
If you need to publish a prerelease to testpypi for development, open a draft PR against main using a branch name that 
begins with `prebuild-`. Each commit to this branch will create a release in testpypi matching the current released version
and ending in `.dev<buildnumber>`.

## Using python registries other than pypi
Prebuilds and release candidates are published to testpypi rather than pypi. To use these images locally you'll need to
use the following:

**Using the release on pypi whose version matches your current sdk (the default)**<br>
```
orchestrate env activate local --registry pypi
``` 

**Using the release on testpypi**<br>
When testing a prerelease, your local SDK version will not match what is locally defined by the SDK. In order to 
use one of these builds you will want to reference the comment on your pull request stating how to do so. The key
differentiator being you need to specify a release version number as seen below.
```
orchestrate env activate local --registry testpypi --test-package-version-override <release version number>
``` 

**Using a locally built package**<br>
If you are doing local development you may want to build your package and test it locally against your local orchestrate
server. This is done by building the package with `hatch build`, and copying the wheel file out of the dist folder and
sticking it in `src/docker/sdk` folder. This folder will be volume mounted into the /packages folder that can be installed
by path by within the tool manager runtime.

Make sure to update the referenced file in `ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.publish_or_update_tools`.
And then you can switch to using this image by doing:
```
orchestrate server activate local --registry local
```
