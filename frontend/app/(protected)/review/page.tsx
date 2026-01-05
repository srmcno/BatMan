'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckIcon, XMarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { classificationsApi, speciesApi } from '@/lib/api';

export default function Review() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const queryClient = useQueryClient();

  const { data: pending, isLoading } = useQuery({
    queryKey: ['pending-review'],
    queryFn: () => classificationsApi.getPendingReview(undefined, 1, 50),
  });

  const { data: speciesList } = useQuery({
    queryKey: ['species'],
    queryFn: () => speciesApi.list(),
  });

  const vetMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' }) =>
      classificationsApi.vet(id, { action }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-review'] });
      setCurrentIndex((prev) => prev);
    },
  });

  const items = pending?.data?.items || [];
  const currentItem = items[currentIndex];
  const total = pending?.data?.total || 0;

  const handleApprove = () => {
    if (currentItem) {
      vetMutation.mutate(
        { id: currentItem.id, action: 'approve' },
        {
          onSuccess: () => {
            toast.success('Classification approved');
            if (currentIndex < items.length - 1) {
              setCurrentIndex(currentIndex + 1);
            }
          },
        }
      );
    }
  };

  const handleReject = () => {
    if (currentItem) {
      vetMutation.mutate(
        { id: currentItem.id, action: 'reject' },
        {
          onSuccess: () => {
            toast.success('Classification rejected');
            if (currentIndex < items.length - 1) {
              setCurrentIndex(currentIndex + 1);
            }
          },
        }
      );
    }
  };

  const handleSkip = () => {
    if (currentIndex < items.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <CheckIcon className="h-12 w-12 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">All caught up!</h2>
        <p className="text-gray-400">No classifications pending review.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Review Classifications</h1>
          <p className="mt-2 text-gray-400">
            {currentIndex + 1} of {total} calls to review
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-64 bg-gray-800 rounded-full h-2">
            <div
              className="bg-primary-500 h-2 rounded-full transition-all"
              style={{ width: `${((currentIndex + 1) / items.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {currentItem && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Spectrogram */}
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Spectrogram</h2>
            <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
              {currentItem.call_spectrogram_path ? (
                <img
                  src={currentItem.call_spectrogram_path}
                  alt="Call spectrogram"
                  className="max-w-full max-h-full object-contain"
                />
              ) : (
                <p className="text-gray-500">Spectrogram not available</p>
              )}
            </div>
          </div>

          {/* Classification info */}
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">AI Prediction</h2>

            <div className="space-y-4 mb-6">
              <div className="p-4 bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-400">Species</p>
                <p className="text-xl font-semibold text-white">
                  {currentItem.species_name || currentItem.species_code || 'Unknown'}
                </p>
              </div>

              <div className="p-4 bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-400">Confidence</p>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-700 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${
                        currentItem.confidence >= 0.9
                          ? 'bg-green-500'
                          : currentItem.confidence >= 0.7
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${currentItem.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-white font-medium">
                    {(currentItem.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-800 rounded-lg">
                  <p className="text-sm text-gray-400">Duration</p>
                  <p className="text-lg text-white">{currentItem.duration_ms?.toFixed(1)} ms</p>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg">
                  <p className="text-sm text-gray-400">Activity</p>
                  <p className="text-lg text-white capitalize">{currentItem.activity_type}</p>
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-4">
              <button
                onClick={handleReject}
                disabled={vetMutation.isPending}
                className="flex-1 btn bg-red-600 hover:bg-red-700 text-white"
              >
                <XMarkIcon className="h-5 w-5 mr-2" />
                Reject
              </button>
              <button
                onClick={handleSkip}
                disabled={vetMutation.isPending}
                className="btn-secondary"
              >
                <ArrowPathIcon className="h-5 w-5" />
              </button>
              <button
                onClick={handleApprove}
                disabled={vetMutation.isPending}
                className="flex-1 btn bg-green-600 hover:bg-green-700 text-white"
              >
                <CheckIcon className="h-5 w-5 mr-2" />
                Approve
              </button>
            </div>

            <p className="text-center text-sm text-gray-500 mt-4">
              Press A to approve, D to reject, S to skip
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
