import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type { Alert } from '@/types/risk'

export function useAlerts(userId?: string, limit = 20) {
  return useQuery<Alert[]>({
    queryKey: ['alerts', userId, limit],
    queryFn: async () => {
      try {
        // Alert Notification Service endpoint
        const alertServiceUrl =
          import.meta.env.VITE_ALERT_NOTIFICATION_URL ||
          'https://alert-notification-service-961424092563.us-central1.run.app'

        const response = await apiClient.get(`${alertServiceUrl}/api/v1/notifications`, {
          params: {
            limit,
            acknowledged: false,
            ...(userId && { user_id: userId }),
          },
        })

        return response.data.alerts || response.data || []
      } catch (error) {
        // Return empty array if API call fails (alerts are optional)
        console.warn('Failed to fetch alerts:', error)
        return []
      }
    },
    enabled: true,
    refetchInterval: 10000, // Refetch every 10 seconds for real-time alerts
    retry: 1,
  })
}
