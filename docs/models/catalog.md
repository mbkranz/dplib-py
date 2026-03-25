# Catalog

The Data Catalog model allows to manipulate a Pydantic model in Python for managing a collection of Data Packages.

## Usage

```python
from dplib.models import Catalog, Package, Resource

catalog = Catalog()
catalog.name = 'my-catalog'

package = Package(name='my-package')
package.add_resource(Resource(name='table', path='table.csv'))
catalog.add_package(package)

print(catalog.to_text(format="json"))
```

```json
{
  "name": "my-catalog",
  "packages": [
    {
      "name": "my-package",
      "resources": [
        {
          "name": "table",
          "path": "table.csv"
        }
      ]
    }
  ]
}
```

## Accessing Entities

Use ``get_entity`` with dot notation to access packages and resources:

```python
# Get a package
package = catalog.get_entity("my-package")

# Get a resource within a package
resource = catalog.get_entity("my-package.table")
```

## Reference

::: dplib.models.Catalog
