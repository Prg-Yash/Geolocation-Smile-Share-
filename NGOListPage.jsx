// Function to fetch nearby NGOs from API
const fetchNearbyNGOs = async (latitude, longitude) => {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/nearby-ngos/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          latitude,
          longitude,
          radius: 50, // 50km radius
        }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error("API Error:", errorData);
      throw new Error(errorData.detail || "Failed to fetch nearby NGOs");
    }

    const data = await response.json();
    console.log("Nearby NGOs:", data); // Debug log

    // Sort NGOs by distance
    const sortedNGOs = data.sort((a, b) => a.distance - b.distance);
    setNearbyNGOs(sortedNGOs);
    return sortedNGOs;
  } catch (error) {
    console.error("Error fetching nearby NGOs:", error);
    setLocationError("Failed to fetch nearby NGOs. Please try again later.");
    return [];
  }
};
