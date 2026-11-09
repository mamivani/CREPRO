'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/services/api';
import { Property } from '@/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function PropertiesPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    address: '',
    city: '',
    state: '',
    zip_code: '',
    property_type: 'apartment',
    unit_count: 1,
  });

  useEffect(() => {
    loadProperties();
  }, []);

  const loadProperties = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getProperties(0, 10);
      setProperties(response.data);
    } catch (error) {
      console.error('Failed to load properties:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.createProperty(formData);
      setFormData({
        name: '',
        address: '',
        city: '',
        state: '',
        zip_code: '',
        property_type: 'apartment',
        unit_count: 1,
      });
      setShowForm(false);
      await loadProperties();
    } catch (error) {
      console.error('Failed to create property:', error);
    }
  };

  return (
    <div className="space-y-6" data-testid="properties-page">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold">Properties</h2>
          <p className="text-muted-foreground">Manage your properties</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} data-testid="create-property-button">
          {showForm ? 'Cancel' : 'Add Property'}
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Property</CardTitle>
            <CardDescription>Fill in the details to add a new property</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4" data-testid="property-form">
              <div>
                <label htmlFor="name" className="text-sm font-medium">
                  Name
                </label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  data-testid="property-name-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="address" className="text-sm font-medium">
                    Address
                  </label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label htmlFor="city" className="text-sm font-medium">
                    City
                  </label>
                  <Input
                    id="city"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="state" className="text-sm font-medium">
                    State
                  </label>
                  <Input
                    id="state"
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label htmlFor="zip" className="text-sm font-medium">
                    ZIP Code
                  </label>
                  <Input
                    id="zip"
                    value={formData.zip_code}
                    onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="type" className="text-sm font-medium">
                    Type
                  </label>
                  <select
                    id="type"
                    value={formData.property_type}
                    onChange={(e) => setFormData({ ...formData, property_type: e.target.value })}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="apartment">Apartment</option>
                    <option value="house">House</option>
                    <option value="commercial">Commercial</option>
                    <option value="industrial">Industrial</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="units" className="text-sm font-medium">
                    Unit Count
                  </label>
                  <Input
                    id="units"
                    type="number"
                    min="1"
                    value={formData.unit_count}
                    onChange={(e) =>
                      setFormData({ ...formData, unit_count: parseInt(e.target.value) })
                    }
                    required
                  />
                </div>
              </div>
              <Button type="submit" className="w-full" data-testid="submit-property-button">
                Create Property
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Properties List */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Loading properties...</p>
        </div>
      ) : properties.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No properties found. Create one to get started.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {properties.map((property) => (
            <Card key={property.id} data-testid={`property-card-${property.id}`}>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-semibold">{property.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {property.address}, {property.city}, {property.state} {property.zip_code}
                    </p>
                    <div className="mt-2 flex gap-4 text-sm">
                      <span className="text-muted-foreground">Type: {property.property_type}</span>
                      <span className="text-muted-foreground">Units: {property.unit_count}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      data-testid={`view-property-button-${property.id}`}
                    >
                      View
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      data-testid={`edit-property-button-${property.id}`}
                    >
                      Edit
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
