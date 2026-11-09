import React, { useState } from 'react';
import {
  View,
  Image,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
  TouchableOpacity,
  Text,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Input } from '@/components/Input';
import { mobileApiClient } from '@/services/api';
import { CreatePropertyInput } from '@/types';
import { Ionicons } from '@expo/vector-icons';

export default function CreatePropertyScreen() {
  const [formData, setFormData] = useState<Partial<CreatePropertyInput>>({
    address: '',
    city: '',
    state: '',
    zipcode: '',
    country: 'USA',
    property_type: 'Residential',
    bedrooms: 0,
    bathrooms: 0,
    square_feet: 0,
    year_built: new Date().getFullYear(),
  });

  const [photos, setPhotos] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled) {
        setPhotos([...photos, result.assets[0].uri]);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to capture photo');
    }
  };

  const pickImageFromLibrary = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled) {
        setPhotos([...photos, result.assets[0].uri]);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to pick image');
    }
  };

  const removePhoto = (index: number) => {
    setPhotos(photos.filter((_, i) => i !== index));
  };

  const handleCreateProperty = async () => {
    if (!formData.address || !formData.city || !formData.state) {
      Alert.alert('Validation Error', 'Please fill in all required fields');
      return;
    }

    try {
      setLoading(true);
      await mobileApiClient.createProperty(formData);
      
      // TODO: Upload photos to backend
      if (photos.length > 0) {
        // Implement photo upload
      }

      Alert.alert('Success', 'Property created successfully');
      // Reset form and navigate back
    } catch (error) {
      Alert.alert('Error', mobileApiClient.getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Card>
        <Text style={styles.sectionTitle}>Property Information</Text>

        <Input
          label="Address"
          placeholder="123 Main St"
          value={formData.address || ''}
          onChangeText={(text) => setFormData({ ...formData, address: text })}
        />

        <Input
          label="City"
          placeholder="New York"
          value={formData.city || ''}
          onChangeText={(text) => setFormData({ ...formData, city: text })}
        />

        <Input
          label="State"
          placeholder="NY"
          value={formData.state || ''}
          onChangeText={(text) => setFormData({ ...formData, state: text })}
        />

        <Input
          label="Zip Code"
          placeholder="10001"
          value={formData.zipcode || ''}
          onChangeText={(text) => setFormData({ ...formData, zipcode: text })}
          keyboardType="numeric"
        />

        <Input
          label="Bedrooms"
          placeholder="3"
          value={String(formData.bedrooms || '')}
          onChangeText={(text) =>
            setFormData({ ...formData, bedrooms: parseInt(text) || 0 })
          }
          keyboardType="numeric"
        />

        <Input
          label="Bathrooms"
          placeholder="2"
          value={String(formData.bathrooms || '')}
          onChangeText={(text) =>
            setFormData({ ...formData, bathrooms: parseInt(text) || 0 })
          }
          keyboardType="numeric"
        />

        <Input
          label="Square Feet"
          placeholder="2500"
          value={String(formData.square_feet || '')}
          onChangeText={(text) =>
            setFormData({ ...formData, square_feet: parseInt(text) || 0 })
          }
          keyboardType="numeric"
        />

        <Input
          label="Year Built"
          placeholder={String(new Date().getFullYear())}
          value={String(formData.year_built || '')}
          onChangeText={(text) =>
            setFormData({ ...formData, year_built: parseInt(text) || 0 })
          }
          keyboardType="numeric"
        />
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Property Photos</Text>
        <Text style={styles.subtitle}>Add property photos for documentation</Text>

        {photos.length > 0 && (
          <View style={styles.photoGrid}>
            {photos.map((photo, index) => (
              <View key={index} style={styles.photoContainer}>
                <Image source={{ uri: photo }} style={styles.photo} />
                <TouchableOpacity
                  style={styles.removeButton}
                  onPress={() => removePhoto(index)}
                >
                  <Ionicons name="close-circle" size={24} color="#DC2626" />
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}

        <View style={styles.buttonGroup}>
          <Button
            title="📷 Take Photo"
            onPress={pickImage}
            variant="secondary"
          />
          <Button
            title="🖼️ Choose Image"
            onPress={pickImageFromLibrary}
            variant="secondary"
          />
        </View>

        {photos.length > 0 && (
          <Text style={styles.photoCount}>
            {photos.length} photo{photos.length !== 1 ? 's' : ''} selected
          </Text>
        )}
      </Card>

      <Card>
        <Button
          title={loading ? 'Creating...' : 'Create Property'}
          onPress={handleCreateProperty}
          disabled={loading}
          variant="primary"
        />
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 12,
    backgroundColor: '#F9FAFB',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
    color: '#1F2937',
  },
  subtitle: {
    fontSize: 13,
    color: '#6B7280',
    marginBottom: 12,
  },
  photoGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  photoContainer: {
    position: 'relative',
    marginRight: 8,
    marginBottom: 8,
  },
  photo: {
    width: 80,
    height: 80,
    borderRadius: 8,
  },
  removeButton: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
  },
  buttonGroup: {
    flexDirection: 'row',
    gap: 8,
  },
  photoCount: {
    marginTop: 12,
    fontSize: 13,
    color: '#6B7280',
    textAlign: 'center',
  },
});
