"""Bit of a basemodel template."""

from pydantic import BaseModel


class BaseModelF(BaseModel):
    """Flexible update BaseModel."""

    def update(self, **settings):
        """Update the settings with new ones."""
        updated = self.model_validate(
            {**self.to_dict(), **settings},
            context=self.context,
        )
        self.__dict__.update(updated)
