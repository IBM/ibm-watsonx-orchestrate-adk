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


### Running tests and code coverage

You can run `hatch run test` to run the tests for both the CLI and SDK and `hatch run cov` to see the test coverage

